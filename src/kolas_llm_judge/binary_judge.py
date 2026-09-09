from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from .models import EvaluationScenario, GeneratedRisk, ReferenceRisk
from .qualification_controls import QualificationControl


class MatchChecklistDecision(BaseModel):
    id: str
    same_hazard_mechanism: bool
    context_compatible: bool
    accident_compatible: bool

    @property
    def is_match(self) -> bool:
        return (
            self.same_hazard_mechanism
            and self.context_compatible
            and self.accident_compatible
        )


class MatchChecklistBatch(BaseModel):
    rows: list[MatchChecklistDecision]


class QualityChecklistDecision(BaseModel):
    id: str
    mitigation_addresses_hazard: bool
    mitigation_actionable: bool
    mitigation_specific: bool
    unsafe_advice: bool
    legal_basis_relevant: bool


class QualityChecklistBatch(BaseModel):
    rows: list[QualityChecklistDecision]


class SafetyChecklistDecision(BaseModel):
    id: str
    critical_safety_error: bool


class SafetyChecklistBatch(BaseModel):
    rows: list[SafetyChecklistDecision]


@dataclass(frozen=True)
class BinaryJudgeConfig:
    model: str = "gpt-5.6-sol"
    reasoning_effort: str = "medium"
    max_concurrency: int = 8
    request_timeout_seconds: float = 180.0
    max_retries: int = 3
    pipeline_version: str = "binary-checklist-v1"
    prompt_path: Path = Path("prompts/judge_binary_v1.md")
    rubric_path: Path = Path("configs/rubric_binary_v1.yaml")

    @classmethod
    def from_env(cls) -> "BinaryJudgeConfig":
        return cls(
            model=os.getenv("JUDGE_MODEL", cls.model),
            reasoning_effort=os.getenv(
                "JUDGE_REASONING_EFFORT",
                cls.reasoning_effort,
            ),
            max_concurrency=max(
                1,
                int(
                    os.getenv(
                        "BINARY_JUDGE_MAX_CONCURRENCY",
                        str(cls.max_concurrency),
                    )
                ),
            ),
            request_timeout_seconds=max(
                30.0,
                float(
                    os.getenv(
                        "BINARY_JUDGE_TIMEOUT_SECONDS",
                        str(cls.request_timeout_seconds),
                    )
                ),
            ),
            max_retries=max(
                0,
                int(
                    os.getenv(
                        "BINARY_JUDGE_MAX_RETRIES",
                        str(cls.max_retries),
                    )
                ),
            ),
        )


@dataclass
class BinaryJudgeCall:
    stage: str
    rows: list[BaseModel]
    response_id: str | None
    response_model: str | None
    usage: dict[str, Any] | None
    elapsed_ms: int


class BinaryChecklistJudge:
    def __init__(
        self,
        config: BinaryJudgeConfig | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = config or BinaryJudgeConfig.from_env()
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for Binary Checklist Judge")
        self.client = AsyncOpenAI(
            api_key=key,
            timeout=self.config.request_timeout_seconds,
            max_retries=self.config.max_retries,
        )
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)

    def _instructions(self) -> str:
        prompt = self.config.prompt_path.read_text(encoding="utf-8")
        rubric = self.config.rubric_path.read_text(encoding="utf-8")
        return f"{prompt}\n\nFrozen rubric:\n{rubric}"

    async def _parse(
        self,
        *,
        stage: str,
        payload: dict[str, Any],
        text_format: type[BaseModel],
    ) -> BinaryJudgeCall:
        started = time.perf_counter()
        async with self._semaphore:
            response = await self.client.responses.parse(
                model=self.config.model,
                instructions=self._instructions(),
                input=json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                text_format=text_format,
                reasoning={"effort": self.config.reasoning_effort},
                store=False,
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(f"Binary Judge {stage} returned no parsed output")
        usage = (
            response.usage.model_dump(mode="json")
            if getattr(response, "usage", None)
            else None
        )
        return BinaryJudgeCall(
            stage=stage,
            rows=list(parsed.rows),
            response_id=getattr(response, "id", None),
            response_model=getattr(response, "model", None),
            usage=usage,
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _validate_ids(expected: list[str], rows: list[BaseModel], stage: str) -> None:
        actual = [str(getattr(row, "id")) for row in rows]
        if len(actual) != len(set(actual)) or set(actual) != set(expected):
            raise ValueError(
                f"Binary Judge {stage} completeness failure: "
                f"expected={len(expected)}, actual={len(actual)}, "
                f"missing={sorted(set(expected) - set(actual))[:10]}, "
                f"extra={sorted(set(actual) - set(expected))[:10]}"
            )

    async def evaluate_match_controls(
        self,
        controls: list[QualificationControl],
    ) -> BinaryJudgeCall:
        rows = [
            {
                "id": control.control_id,
                "process": control.process,
                "reference": {
                    "hazard": control.reference_hazard,
                    "accident_type": control.reference_accident_type,
                },
                "generated": {
                    "hazard": control.generated_hazard,
                    "accident_type": control.generated_accident_type,
                },
            }
            for control in controls
        ]
        call = await self._parse(
            stage="match",
            payload={
                "task": "Evaluate every row using MATCH checklist booleans.",
                "row_count": len(rows),
                "rows": rows,
            },
            text_format=MatchChecklistBatch,
        )
        self._validate_ids([x.control_id for x in controls], call.rows, "match")
        return call

    async def evaluate_quality_controls(
        self,
        controls: list[QualificationControl],
    ) -> BinaryJudgeCall:
        rows = [
            {
                "id": control.control_id,
                "process": control.process,
                "hazard": control.reference_hazard,
                "reference_mitigation": control.reference_mitigation,
                "reference_legal_basis": control.reference_legal_basis,
                "generated_mitigation": control.generated_mitigation,
                "generated_legal_basis": control.generated_legal_basis,
            }
            for control in controls
        ]
        call = await self._parse(
            stage="quality",
            payload={
                "task": "Evaluate every row using QUALITY checklist booleans.",
                "row_count": len(rows),
                "rows": rows,
            },
            text_format=QualityChecklistBatch,
        )
        self._validate_ids([x.control_id for x in controls], call.rows, "quality")
        return call

    async def evaluate_safety_controls(
        self,
        controls: list[QualificationControl],
    ) -> BinaryJudgeCall:
        rows = [
            {
                "id": control.control_id,
                "process": control.process,
                "hazard": control.reference_hazard,
                "mitigation": control.generated_mitigation,
            }
            for control in controls
        ]
        call = await self._parse(
            stage="safety",
            payload={
                "task": "Evaluate every row using SAFETY checklist boolean.",
                "row_count": len(rows),
                "rows": rows,
            },
            text_format=SafetyChecklistBatch,
        )
        self._validate_ids([x.control_id for x in controls], call.rows, "safety")
        return call

    async def evaluate_match_pairs(
        self,
        scenario: EvaluationScenario,
        pairs: list[tuple[ReferenceRisk, GeneratedRisk]],
    ) -> BinaryJudgeCall:
        rows = [
            {
                "id": f"{reference.reference_id}::{risk.generated_id}",
                "process": scenario.input.process,
                "subprocess": scenario.input.subprocess,
                "reference": {
                    "hazard": reference.hazard,
                    "accident_types": reference.accident_types,
                },
                "generated": {
                    "hazard": risk.hazard,
                    "risk_cause": risk.risk_cause,
                    "accident_types": risk.accident_types,
                },
            }
            for reference, risk in pairs
        ]
        call = await self._parse(
            stage="match",
            payload={
                "task": "Evaluate every reference-generated pair using MATCH checklist booleans.",
                "row_count": len(rows),
                "rows": rows,
            },
            text_format=MatchChecklistBatch,
        )
        self._validate_ids([row["id"] for row in rows], call.rows, "match")
        return call

    async def evaluate_quality_pairs(
        self,
        scenario: EvaluationScenario,
        pairs: list[tuple[ReferenceRisk, GeneratedRisk]],
    ) -> BinaryJudgeCall:
        rows = [
            {
                "id": f"{reference.reference_id}::{risk.generated_id}",
                "process": scenario.input.process,
                "subprocess": scenario.input.subprocess,
                "hazard": reference.hazard,
                "reference_mitigation": reference.mitigation,
                "reference_legal_basis": reference.legal_basis,
                "generated_mitigation": risk.mitigation,
                "generated_legal_basis": risk.legal_basis,
            }
            for reference, risk in pairs
        ]
        call = await self._parse(
            stage="quality",
            payload={
                "task": "Evaluate already-matched pairs using QUALITY checklist booleans.",
                "row_count": len(rows),
                "rows": rows,
            },
            text_format=QualityChecklistBatch,
        )
        self._validate_ids([row["id"] for row in rows], call.rows, "quality")
        return call
