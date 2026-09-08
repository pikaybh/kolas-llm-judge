from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .matching import select_match_ids
from .models import (
    CaseJudgeResult,
    EvaluationScenario,
    GeneratedBatchJudgeResult,
    GeneratedJudgeResult,
    GeneratedRisk,
    PairJudgeResult,
    PairMatchBatchJudgeResult,
    PairQualityBatchJudgeResult,
)


@dataclass(frozen=True)
class JudgeConfig:
    model: str = "gpt-5.6-sol"
    reasoning_effort: str = "medium"
    max_pairs_per_call: int = 80
    max_concurrency: int = 3
    request_timeout_seconds: float = 300.0
    max_retries: int = 3
    pipeline_version: str = "two-stage-v1"
    prompt_path: Path = Path(
        "prompts/judge_v1.md"
    )
    rubric_path: Path = Path(
        "configs/rubric_v1.yaml"
    )

    @classmethod
    def from_env(cls) -> "JudgeConfig":
        return cls(
            model=os.getenv(
                "JUDGE_MODEL",
                cls.model,
            ),
            reasoning_effort=os.getenv(
                "JUDGE_REASONING_EFFORT",
                cls.reasoning_effort,
            ),
            max_pairs_per_call=max(
                1,
                int(
                    os.getenv(
                        "JUDGE_MAX_PAIRS_PER_CALL",
                        str(
                            cls.max_pairs_per_call
                        ),
                    )
                ),
            ),
            max_concurrency=max(
                1,
                int(
                    os.getenv(
                        "JUDGE_MAX_CONCURRENCY",
                        str(cls.max_concurrency),
                    )
                ),
            ),
            request_timeout_seconds=max(
                30.0,
                float(
                    os.getenv(
                        "JUDGE_TIMEOUT_SECONDS",
                        str(
                            cls
                            .request_timeout_seconds
                        ),
                    )
                ),
            ),
            max_retries=max(
                0,
                int(
                    os.getenv(
                        "JUDGE_MAX_RETRIES",
                        str(cls.max_retries),
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


def _match_reference_payload(
    reference: Any,
) -> dict[str, Any]:
    return {
        "reference_id": reference.reference_id,
        "hazard": reference.hazard,
        "accident_types": (
            reference.accident_types
        ),
    }


def _match_generated_payload(
    risk: GeneratedRisk,
) -> dict[str, Any]:
    return {
        "generated_id": risk.generated_id,
        "hazard": risk.hazard,
        "risk_cause": risk.risk_cause,
        "accident_types": risk.accident_types,
    }


def build_pair_batch_input(
    scenario: EvaluationScenario,
    pairs: list[
        tuple[Any, GeneratedRisk]
    ],
) -> str:
    """Build the stage-1 match payload.

    Mitigation/legal fields are intentionally
    excluded so downstream quality cannot
    influence semantic matching.
    """
    references: dict[
        str,
        Any,
    ] = {}
    generated: dict[
        str,
        GeneratedRisk,
    ] = {}
    pair_ids: list[
        dict[str, str]
    ] = []
    for reference, risk in pairs:
        references[
            reference.reference_id
        ] = reference
        generated[
            risk.generated_id
        ] = risk
        pair_ids.append(
            {
                "reference_id": (
                    reference.reference_id
                ),
                "generated_id": (
                    risk.generated_id
                ),
            }
        )
    payload = {
        "task": (
            "MATCH_STAGE: evaluate only hazard "
            "semantic_match and accident_type_correctness "
            "for exactly the listed pairs. "
            "Do not evaluate mitigation or legal basis."
        ),
        "requirements": {
            "pair_count": len(pairs),
            "include_every_pair_exactly_once": (
                True
            ),
            "explanation_max_words": 18,
        },
        "scenario_input": (
            scenario.input.model_dump(
                mode="json"
            )
        ),
        "references": [
            _match_reference_payload(
                value
            )
            for value in references.values()
        ],
        "generated_risks": [
            _match_generated_payload(
                value
            )
            for value in generated.values()
        ],
        "pairs": pair_ids,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_quality_batch_input(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    matched_ids: list[
        tuple[str, str]
    ],
) -> str:
    references = {
        item.reference_id: item
        for item in scenario.references
    }
    generated_map = {
        item.generated_id: item
        for item in generated
    }
    rows: list[
        dict[str, Any]
    ] = []
    for reference_id, generated_id in (
        matched_ids
    ):
        reference = references[
            reference_id
        ]
        risk = generated_map[generated_id]
        rows.append(
            {
                "reference_id": (
                    reference_id
                ),
                "generated_id": (
                    generated_id
                ),
                "reference": {
                    "hazard": (
                        reference.hazard
                    ),
                    "mitigation": (
                        reference.mitigation
                    ),
                    "legal_basis": (
                        reference.legal_basis
                    ),
                },
                "generated": {
                    "hazard": risk.hazard,
                    "risk_cause": (
                        risk.risk_cause
                    ),
                    "mitigation": (
                        risk.mitigation
                    ),
                    "legal_basis": (
                        risk.legal_basis
                    ),
                },
            }
        )
    payload = {
        "task": (
            "QUALITY_STAGE: these pairs are already "
            "matched by hazard semantics. Evaluate only "
            "mitigation appropriateness, mitigation "
            "specificity, and legal-basis relevance."
        ),
        "requirements": {
            "pair_count": len(rows),
            "include_every_pair_exactly_once": (
                True
            ),
            "explanation_max_words": 18,
        },
        "scenario_input": (
            scenario.input.model_dump(
                mode="json"
            )
        ),
        "matched_pairs": rows,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_generated_batch_input(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
) -> str:
    payload = {
        "task": (
            "SAFETY_STAGE: evaluate every generated "
            "risk for unsupported_claim and "
            "critical_safety_error only."
        ),
        "requirements": {
            "generated_count": (
                len(generated)
            ),
            "include_every_generated_id_exactly_once": (
                True
            ),
            "explanation_max_words": 18,
        },
        "scenario_input": (
            scenario.input.model_dump(
                mode="json"
            )
        ),
        "generated_risks": [
            {
                "generated_id": (
                    risk.generated_id
                ),
                "hazard": risk.hazard,
                "risk_cause": (
                    risk.risk_cause
                ),
                "accident_types": (
                    risk.accident_types
                ),
                "mitigation": (
                    risk.mitigation
                ),
            }
            for risk in generated
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def iter_pair_batches(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    batch_size: int,
) -> list[
    list[tuple[Any, GeneratedRisk]]
]:
    all_pairs = [
        (reference, risk)
        for reference
        in scenario.references
        for risk in generated
    ]
    return [
        all_pairs[
            index : index + batch_size
        ]
        for index in range(
            0,
            len(all_pairs),
            batch_size,
        )
    ]


def validate_judge_completeness(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    result: CaseJudgeResult,
) -> None:
    expected_pairs = {
        (
            reference.reference_id,
            risk.generated_id,
        )
        for reference
        in scenario.references
        for risk in generated
    }
    actual_pairs = {
        (
            pair.reference_id,
            pair.generated_id,
        )
        for pair
        in result.pair_evaluations
    }
    if (
        actual_pairs != expected_pairs
        or len(
            result.pair_evaluations
        )
        != len(expected_pairs)
    ):
        missing = sorted(
            expected_pairs - actual_pairs
        )[:10]
        extra = sorted(
            actual_pairs - expected_pairs
        )[:10]
        raise ValueError(
            "Incomplete judge pair matrix: "
            f"missing={missing}, extra={extra}"
        )

    expected_generated = {
        risk.generated_id
        for risk in generated
    }
    actual_generated = {
        item.generated_id
        for item
        in result.generated_evaluations
    }
    if (
        actual_generated
        != expected_generated
        or len(
            result.generated_evaluations
        )
        != len(expected_generated)
    ):
        raise ValueError(
            "Incomplete generated-risk "
            "judge evaluations"
        )


def validate_quality_completeness(
    result: CaseJudgeResult,
    matched_ids: list[
        tuple[str, str]
    ],
) -> None:
    pair_map = {
        (
            pair.reference_id,
            pair.generated_id,
        ): pair
        for pair in result.pair_evaluations
    }
    missing = [
        key
        for key in matched_ids
        if (
            key not in pair_map
            or not pair_map[
                key
            ].quality_evaluated
        )
    ]
    if missing:
        raise ValueError(
            "Missing matched-pair quality "
            f"evaluations: {missing[:10]}"
        )


def _response_metadata(
    response: Any,
    *,
    stage: str,
    batch_index: int | None,
    item_count: int,
    elapsed_ms: int,
) -> dict[str, Any]:
    usage = (
        response.usage.model_dump(
            mode="json"
        )
        if getattr(
            response,
            "usage",
            None,
        )
        else None
    )
    return {
        "stage": stage,
        "batch_index": batch_index,
        "item_count": item_count,
        "elapsed_ms": elapsed_ms,
        "response_id": getattr(
            response,
            "id",
            None,
        ),
        "response_model": getattr(
            response,
            "model",
            None,
        ),
        "usage": usage,
    }


class LlmJudge:
    def __init__(
        self,
        config: JudgeConfig | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = (
            config
            or JudgeConfig.from_env()
        )
        key = (
            api_key
            or os.getenv(
                "OPENAI_API_KEY"
            )
        )
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is required "
                "for LLM Judge execution"
            )
        self.client = AsyncOpenAI(
            api_key=key,
            timeout=(
                self.config
                .request_timeout_seconds
            ),
            max_retries=(
                self.config.max_retries
            ),
        )
        self._semaphore = (
            asyncio.Semaphore(
                self.config.max_concurrency
            )
        )

    def _instructions(self) -> str:
        prompt = (
            self.config.prompt_path
            .read_text(
                encoding="utf-8"
            )
        )
        rubric = (
            self.config.rubric_path
            .read_text(
                encoding="utf-8"
            )
        )
        return (
            f"{prompt}\n\n"
            f"평가 rubric 원문:\n{rubric}\n\n"
            "단계별 task에 명시되지 않은 차원은 평가하지 마세요. "
            "MATCH_STAGE는 설명을 출력하지 않습니다. QUALITY/SAFETY의 "
            "e는 한 문장, 18단어 이하의 핵심 근거만 작성하되, "
            "SAFETY에서 u와 c가 모두 false이면 e는 빈 문자열로 둡니다."
        )

    async def _parse(
        self,
        *,
        input_text: str,
        text_format: type[Any],
        stage: str,
        batch_index: int | None,
        item_count: int,
    ) -> tuple[
        Any,
        dict[str, Any],
    ]:
        async with self._semaphore:
            started = (
                time.perf_counter()
            )
            response = (
                await self.client
                .responses.parse(
                    model=(
                        self.config.model
                    ),
                    instructions=(
                        self._instructions()
                    ),
                    input=input_text,
                    text_format=(
                        text_format
                    ),
                    reasoning={
                        "effort": (
                            self.config
                            .reasoning_effort
                        )
                    },
                    store=False,
                )
            )
            elapsed_ms = round(
                (
                    time.perf_counter()
                    - started
                )
                * 1000
            )
        metadata = (
            _response_metadata(
                response,
                stage=stage,
                batch_index=(
                    batch_index
                ),
                item_count=item_count,
                elapsed_ms=elapsed_ms,
            )
        )
        return response, metadata

    async def _match_batch(
        self,
        scenario: EvaluationScenario,
        batch: list[
            tuple[Any, GeneratedRisk]
        ],
        batch_index: int,
    ) -> tuple[
        list[Any],
        dict[str, Any],
    ]:
        response, metadata = (
            await self._parse(
                input_text=(
                    build_pair_batch_input(
                        scenario,
                        batch,
                    )
                ),
                text_format=(
                    PairMatchBatchJudgeResult
                ),
                stage="match",
                batch_index=batch_index,
                item_count=len(batch),
            )
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(
                "Judge match batch returned "
                "no parsed output"
            )
        expected = {
            (
                reference.reference_id,
                risk.generated_id,
            )
            for reference, risk
            in batch
        }
        actual = {
            (pair.r, pair.g)
            for pair in parsed.rows
        }
        if (
            actual != expected
            or len(parsed.rows)
            != len(expected)
        ):
            raise ValueError(
                "Incomplete Judge match "
                "batch output"
            )
        return (
            parsed.rows,
            metadata,
        )

    async def _generated_safety(
        self,
        scenario: EvaluationScenario,
        generated: list[GeneratedRisk],
    ) -> tuple[
        list[GeneratedJudgeResult],
        dict[str, Any],
    ]:
        response, metadata = (
            await self._parse(
                input_text=(
                    build_generated_batch_input(
                        scenario,
                        generated,
                    )
                ),
                text_format=(
                    GeneratedBatchJudgeResult
                ),
                stage="safety",
                batch_index=None,
                item_count=len(generated),
            )
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(
                "Judge safety batch returned "
                "no parsed output"
            )
        expected = {
            risk.generated_id
            for risk in generated
        }
        actual = {
            item.g
            for item in parsed.rows
        }
        if (
            actual != expected
            or len(parsed.rows)
            != len(expected)
        ):
            raise ValueError(
                "Incomplete Judge safety "
                "batch output"
            )
        normalized = [
            GeneratedJudgeResult(
                generated_id=item.g,
                unsupported_claim=item.u,
                critical_safety_error=item.c,
                explanation=item.e,
            )
            for item in parsed.rows
        ]
        return (normalized, metadata)

    async def _quality_batch(
        self,
        scenario: EvaluationScenario,
        generated: list[GeneratedRisk],
        matched_ids: list[
            tuple[str, str]
        ],
    ) -> tuple[
        list[Any],
        dict[str, Any],
    ]:
        response, metadata = (
            await self._parse(
                input_text=(
                    build_quality_batch_input(
                        scenario,
                        generated,
                        matched_ids,
                    )
                ),
                text_format=(
                    PairQualityBatchJudgeResult
                ),
                stage="quality",
                batch_index=None,
                item_count=len(
                    matched_ids
                ),
            )
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(
                "Judge quality batch returned "
                "no parsed output"
            )
        expected = set(matched_ids)
        actual = {
            (pair.r, pair.g)
            for pair in parsed.rows
        }
        if (
            actual != expected
            or len(parsed.rows)
            != len(expected)
        ):
            raise ValueError(
                "Incomplete Judge quality "
                "batch output"
            )
        return (
            parsed.rows,
            metadata,
        )

    async def evaluate_case(
        self,
        scenario: EvaluationScenario,
        generated: list[GeneratedRisk],
    ) -> JudgeCallRecord:
        if not generated:
            return JudgeCallRecord(
                result=CaseJudgeResult(
                    pair_evaluations=[],
                    generated_evaluations=[],
                ),
                response_id=None,
                response_model=None,
                usage={
                    "call_count": 0,
                    "calls": [],
                },
                calls=[],
            )

        batches = iter_pair_batches(
            scenario,
            generated,
            self.config
            .max_pairs_per_call,
        )
        match_tasks = [
            self._match_batch(
                scenario,
                batch,
                index,
            )
            for index, batch
            in enumerate(
                batches,
                start=1,
            )
        ]

        safety_task = (
            self._generated_safety(
                scenario,
                generated,
            )
        )
        combined = await asyncio.gather(
            *match_tasks,
            safety_task,
        )

        pair_matches: list[Any] = []
        calls: list[
            dict[str, Any]
        ] = []
        for (
            pair_output,
            metadata,
        ) in combined[
            : len(match_tasks)
        ]:
            pair_matches.extend(
                pair_output
            )
            calls.append(metadata)

        (
            generated_evaluations,
            safety_metadata,
        ) = combined[-1]
        calls.append(safety_metadata)

        normalized_pairs = [
            PairJudgeResult(
                reference_id=pair.r,
                generated_id=pair.g,
                semantic_match=pair.s,
                accident_type_correctness=pair.a,
                mitigation_appropriateness=0,
                mitigation_specificity=0,
                legal_basis_relevance=0,
                quality_evaluated=False,
                explanation="",
            )
            for pair in pair_matches
        ]
        base_result = CaseJudgeResult(
            pair_evaluations=(
                normalized_pairs
            ),
            generated_evaluations=(
                generated_evaluations
            ),
        )
        validate_judge_completeness(
            scenario,
            generated,
            base_result,
        )

        matched_ids = select_match_ids(
            scenario,
            generated,
            base_result,
        )
        if matched_ids:
            (
                qualities,
                quality_metadata,
            ) = await self._quality_batch(
                scenario,
                generated,
                matched_ids,
            )
            calls.append(
                quality_metadata
            )
            quality_map = {
                (
                    item.r,
                    item.g,
                ): item
                for item in qualities
            }
            updated_pairs: list[
                PairJudgeResult
            ] = []
            for pair in normalized_pairs:
                key = (
                    pair.reference_id,
                    pair.generated_id,
                )
                quality = (
                    quality_map.get(key)
                )
                if quality is None:
                    updated_pairs.append(
                        pair
                    )
                    continue
                updated_pairs.append(
                    pair.model_copy(
                        update={
                            "mitigation_appropriateness": (
                                quality.m
                            ),
                            "mitigation_specificity": (
                                quality.p
                            ),
                            "legal_basis_relevance": (
                                quality.l
                            ),
                            "quality_evaluated": (
                                True
                            ),
                            "quality_explanation": (
                                quality.e
                            ),
                        }
                    )
                )
            normalized_pairs = (
                updated_pairs
            )

        result = CaseJudgeResult(
            pair_evaluations=(
                normalized_pairs
            ),
            generated_evaluations=(
                generated_evaluations
            ),
        )
        validate_judge_completeness(
            scenario,
            generated,
            result,
        )
        validate_quality_completeness(
            result,
            matched_ids,
        )

        response_ids = [
            str(
                call["response_id"]
            )
            for call in calls
            if call.get("response_id")
        ]
        response_models = [
            str(
                call[
                    "response_model"
                ]
            )
            for call in calls
            if call.get(
                "response_model"
            )
        ]
        usage = {
            "call_count": len(calls),
            "calls": [
                call.get("usage")
                for call in calls
            ],
        }
        return JudgeCallRecord(
            result=result,
            response_id=(
                ";".join(
                    response_ids
                )
                or None
            ),
            response_model=(
                ";".join(
                    dict.fromkeys(
                        response_models
                    )
                )
                or None
            ),
            usage=usage,
            calls=calls,
        )
