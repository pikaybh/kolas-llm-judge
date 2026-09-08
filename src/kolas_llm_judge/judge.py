from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .models import (
    CaseJudgeResult,
    EvaluationScenario,
    GeneratedBatchJudgeResult,
    GeneratedRisk,
    PairBatchJudgeResult,
)


@dataclass(frozen=True)
class JudgeConfig:
    model: str = "gpt-5.6-sol"
    reasoning_effort: str = "medium"
    max_pairs_per_call: int = 120
    prompt_path: Path = Path("prompts/judge_v1.md")
    rubric_path: Path = Path("configs/rubric_v1.yaml")

    @classmethod
    def from_env(cls) -> "JudgeConfig":
        return cls(
            model=os.getenv("JUDGE_MODEL", cls.model),
            reasoning_effort=os.getenv(
                "JUDGE_REASONING_EFFORT",
                cls.reasoning_effort,
            ),
            max_pairs_per_call=max(
                1,
                int(
                    os.getenv(
                        "JUDGE_MAX_PAIRS_PER_CALL",
                        str(cls.max_pairs_per_call),
                    )
                ),
            ),
        )


@dataclass
class JudgeCallRecord:
    result: CaseJudgeResult
    response_id: str | None
    response_model: str | None
    usage: dict[str, Any] | None
    calls: list[dict[str, Any]] | None = None


def build_judge_input(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
) -> str:
    payload = {
        "task": (
            "Evaluate every reference-generated pair and every generated risk."
        ),
        "requirements": {
            "pair_count": len(scenario.references) * len(generated),
            "generated_count": len(generated),
            "include_every_pair_exactly_once": True,
            "include_every_generated_id_exactly_once": True,
        },
        "scenario_input": scenario.input.model_dump(mode="json"),
        "references": [
            reference.model_dump(mode="json")
            for reference in scenario.references
        ],
        "generated_risks": [
            risk.model_dump(mode="json") for risk in generated
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )


def build_pair_batch_input(
    scenario: EvaluationScenario,
    pairs: list[tuple[Any, GeneratedRisk]],
) -> str:
    references: dict[str, Any] = {}
    generated: dict[str, GeneratedRisk] = {}
    pair_ids: list[dict[str, str]] = []
    for reference, risk in pairs:
        references[reference.reference_id] = reference
        generated[risk.generated_id] = risk
        pair_ids.append(
            {
                "reference_id": reference.reference_id,
                "generated_id": risk.generated_id,
            }
        )
    payload = {
        "task": (
            "Evaluate exactly the listed reference-generated pairs. "
            "Resolve pair IDs against the reference/generated tables. "
            "Do not add or omit pairs."
        ),
        "requirements": {
            "pair_count": len(pairs),
            "include_every_pair_exactly_once": True,
        },
        "scenario_input": scenario.input.model_dump(mode="json"),
        "references": [
            value.model_dump(mode="json")
            for value in references.values()
        ],
        "generated_risks": [
            value.model_dump(mode="json")
            for value in generated.values()
        ],
        "pairs": pair_ids,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )


def build_generated_batch_input(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
) -> str:
    payload = {
        "task": (
            "Evaluate every generated risk for unsupported_claim and "
            "critical_safety_error only."
        ),
        "requirements": {
            "generated_count": len(generated),
            "include_every_generated_id_exactly_once": True,
        },
        "scenario_input": scenario.input.model_dump(mode="json"),
        "generated_risks": [
            risk.model_dump(mode="json") for risk in generated
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )


def iter_pair_batches(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    batch_size: int,
) -> list[list[tuple[Any, GeneratedRisk]]]:
    all_pairs = [
        (reference, risk)
        for reference in scenario.references
        for risk in generated
    ]
    return [
        all_pairs[index : index + batch_size]
        for index in range(0, len(all_pairs), batch_size)
    ]


def validate_judge_completeness(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    result: CaseJudgeResult,
) -> None:
    expected_pairs = {
        (reference.reference_id, risk.generated_id)
        for reference in scenario.references
        for risk in generated
    }
    actual_pairs = {
        (pair.reference_id, pair.generated_id)
        for pair in result.pair_evaluations
    }
    if (
        actual_pairs != expected_pairs
        or len(result.pair_evaluations) != len(expected_pairs)
    ):
        missing = sorted(expected_pairs - actual_pairs)[:10]
        extra = sorted(actual_pairs - expected_pairs)[:10]
        raise ValueError(
            "Incomplete judge pair matrix: "
            f"missing={missing}, extra={extra}"
        )

    expected_generated = {
        risk.generated_id for risk in generated
    }
    actual_generated = {
        item.generated_id
        for item in result.generated_evaluations
    }
    if (
        actual_generated != expected_generated
        or len(result.generated_evaluations)
        != len(expected_generated)
    ):
        raise ValueError(
            "Incomplete generated-risk judge evaluations"
        )


def _response_metadata(response: Any) -> dict[str, Any]:
    usage = (
        response.usage.model_dump(mode="json")
        if getattr(response, "usage", None)
        else None
    )
    return {
        "response_id": getattr(response, "id", None),
        "response_model": getattr(response, "model", None),
        "usage": usage,
    }


class LlmJudge:
    def __init__(
        self,
        config: JudgeConfig | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = config or JudgeConfig.from_env()
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for LLM Judge execution"
            )
        self.client = AsyncOpenAI(api_key=key)

    def _instructions(self) -> str:
        prompt = self.config.prompt_path.read_text(
            encoding="utf-8"
        )
        rubric = self.config.rubric_path.read_text(
            encoding="utf-8"
        )
        return (
            f"{prompt}\n\n평가 rubric 원문:\n{rubric}\n\n"
            "각 explanation은 감사 추적에 필요한 핵심 근거만 "
            "짧게 작성하세요."
        )

    async def _parse(
        self,
        *,
        input_text: str,
        text_format: type[Any],
    ) -> Any:
        return await self.client.responses.parse(
            model=self.config.model,
            instructions=self._instructions(),
            input=input_text,
            text_format=text_format,
            reasoning={
                "effort": self.config.reasoning_effort
            },
            store=False,
        )

    async def evaluate_case(
        self,
        scenario: EvaluationScenario,
        generated: list[GeneratedRisk],
    ) -> JudgeCallRecord:
        pair_count = len(scenario.references) * len(generated)
        if pair_count <= self.config.max_pairs_per_call:
            response = await self._parse(
                input_text=build_judge_input(
                    scenario,
                    generated,
                ),
                text_format=CaseJudgeResult,
            )
            result = response.output_parsed
            if result is None:
                raise RuntimeError(
                    "Judge returned no parsed structured output"
                )
            validate_judge_completeness(
                scenario,
                generated,
                result,
            )
            call = _response_metadata(response)
            return JudgeCallRecord(
                result=result,
                response_id=call["response_id"],
                response_model=call["response_model"],
                usage=call["usage"],
                calls=[call],
            )

        pair_evaluations = []
        calls: list[dict[str, Any]] = []
        for batch in iter_pair_batches(
            scenario,
            generated,
            self.config.max_pairs_per_call,
        ):
            response = await self._parse(
                input_text=build_pair_batch_input(
                    scenario,
                    batch,
                ),
                text_format=PairBatchJudgeResult,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise RuntimeError(
                    "Judge pair batch returned no parsed output"
                )
            expected = {
                (
                    reference.reference_id,
                    risk.generated_id,
                )
                for reference, risk in batch
            }
            actual = {
                (
                    pair.reference_id,
                    pair.generated_id,
                )
                for pair in parsed.pair_evaluations
            }
            if (
                actual != expected
                or len(parsed.pair_evaluations) != len(expected)
            ):
                raise ValueError(
                    "Incomplete Judge pair batch output"
                )
            pair_evaluations.extend(parsed.pair_evaluations)
            calls.append(_response_metadata(response))

        response = await self._parse(
            input_text=build_generated_batch_input(
                scenario,
                generated,
            ),
            text_format=GeneratedBatchJudgeResult,
        )
        generated_output = response.output_parsed
        if generated_output is None:
            raise RuntimeError(
                "Judge generated-risk batch returned no parsed output"
            )
        expected_generated = {
            risk.generated_id for risk in generated
        }
        actual_generated = {
            item.generated_id
            for item in generated_output.generated_evaluations
        }
        if (
            actual_generated != expected_generated
            or len(generated_output.generated_evaluations)
            != len(expected_generated)
        ):
            raise ValueError(
                "Incomplete Judge generated-risk batch output"
            )
        calls.append(_response_metadata(response))

        result = CaseJudgeResult(
            pair_evaluations=pair_evaluations,
            generated_evaluations=(
                generated_output.generated_evaluations
            ),
        )
        validate_judge_completeness(
            scenario,
            generated,
            result,
        )
        response_ids = [
            str(call["response_id"])
            for call in calls
            if call.get("response_id")
        ]
        response_models = [
            str(call["response_model"])
            for call in calls
            if call.get("response_model")
        ]
        usage = {
            "call_count": len(calls),
            "calls": [
                call.get("usage") for call in calls
            ],
        }
        return JudgeCallRecord(
            result=result,
            response_id=";".join(response_ids) or None,
            response_model=";".join(
                dict.fromkeys(response_models)
            )
            or None,
            usage=usage,
            calls=calls,
        )
