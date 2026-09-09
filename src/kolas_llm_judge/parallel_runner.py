from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .binary_evaluation import (
    BinaryCaseEvaluation,
    BinaryEvaluationConfig,
    evaluate_binary_case,
)
from .binary_judge import BinaryChecklistJudge
from .deterministic import (
    evaluate_deterministic,
    post_improvement_mode_for_model_mode,
)
from .io_utils import atomic_write_json, load_json
from .models import (
    DeterministicAssessmentResult,
    EvaluationScenario,
    ParsedRiskAssessment,
)
from .parser import parse_risk_assessment
from .sut_client import (
    SeexrSutClient,
    SutRunResult,
    build_sut_message,
)


AUTOMATED_RUN_NAMESPACE = uuid.UUID("7be0c890-505b-4e68-b75d-bf548b5deab9")


@dataclass(frozen=True)
class ParallelRunnerConfig:
    case_concurrency: int = 24
    sut_concurrency: int = 6
    match_chunk_size: int = 80
    quality_chunk_size: int = 40
    safety_chunk_size: int = 50

    @classmethod
    def from_env(cls) -> "ParallelRunnerConfig":
        return cls(
            case_concurrency=max(
                1,
                int(os.getenv("OFFICIAL_CASE_CONCURRENCY", str(cls.case_concurrency))),
            ),
            sut_concurrency=max(
                1,
                int(os.getenv("OFFICIAL_SUT_CONCURRENCY", str(cls.sut_concurrency))),
            ),
            match_chunk_size=max(
                1,
                int(os.getenv("BINARY_MATCH_CHUNK_SIZE", str(cls.match_chunk_size))),
            ),
            quality_chunk_size=max(
                1,
                int(os.getenv("BINARY_QUALITY_CHUNK_SIZE", str(cls.quality_chunk_size))),
            ),
            safety_chunk_size=max(
                1,
                int(os.getenv("BINARY_SAFETY_CHUNK_SIZE", str(cls.safety_chunk_size))),
            ),
        )

    def binary_config(self) -> BinaryEvaluationConfig:
        return BinaryEvaluationConfig(
            match_chunk_size=self.match_chunk_size,
            quality_chunk_size=self.quality_chunk_size,
            safety_chunk_size=self.safety_chunk_size,
        )


@dataclass
class ParallelRunSummary:
    selected: int
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    active: int = 0

    @property
    def processed(self) -> int:
        return self.completed + self.failed + self.skipped

    def as_dict(self) -> dict[str, int]:
        return {
            "selected": self.selected,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "processed": self.processed,
            "active": self.active,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_paths(run_dir: Path, case_id: str) -> dict[str, Path]:
    root = run_dir / "cases" / case_id
    return {
        "root": root,
        "sut": root / "sut.json",
        "parsed": root / "parsed.json",
        "judge": root / "binary_judge.json",
        "result": root / "result.json",
        "error": root / "error.json",
    }


def _load_sut(path: Path) -> SutRunResult:
    payload = load_json(path)
    return SutRunResult(
        case_id=str(payload["case_id"]),
        session_id=str(payload["session_id"]),
        run_id=str(payload["run_id"]),
        content=str(payload["content"]),
        elapsed_ms=int(payload["elapsed_ms"]),
        events=list(payload.get("events", [])),
        create_run_attempts=int(payload.get("create_run_attempts", 1)),
        stream_reconnects=int(payload.get("stream_reconnects", 0)),
        retry_log=list(payload.get("retry_log", [])),
        auth_recoveries=int(payload.get("auth_recoveries", 0)),
    )


def classify_failure(
    *,
    stage: str,
    exc: BaseException,
    sut_content: str | None = None,
) -> tuple[str, str]:
    message = str(exc)
    content = sut_content or ""
    if stage == "parse":
        if "<ask_user" in content:
            return "sut_non_completion", "ask_user"
        if "Invalid risk_assessment XML" in message:
            return "sut_non_completion", "invalid_risk_assessment_xml"
        if "<risk_assessment> XML block not found" in message:
            return "sut_non_completion", "missing_risk_assessment"
        return "sut_non_completion", "unparseable_sut_output"
    if stage == "sut" and (
        message.startswith("SEEXR run terminated")
        or "has no final content" in message
    ):
        return "sut_non_completion", "sut_run_terminal_failure"
    if stage == "binary_judge":
        return "evaluator_failure", "judge_or_evaluator_failure"
    if stage == "result":
        return "evaluator_failure", "result_assembly_failure"
    if stage == "sut":
        return "infrastructure_failure", "sut_transport_or_api_failure"
    return "evaluator_failure", "unexpected_evaluator_failure"


def _save_error(
    path: Path,
    case_id: str,
    stage: str,
    exc: BaseException,
    *,
    sut_content: str | None = None,
) -> None:
    failure_class, failure_reason = classify_failure(
        stage=stage,
        exc=exc,
        sut_content=sut_content,
    )
    atomic_write_json(
        path,
        {
            "case_id": case_id,
            "stage": stage,
            "failure_class": failure_class,
            "failure_reason": failure_reason,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "failed_at_utc": _utc_now(),
        },
    )


async def process_automated_case(
    *,
    scenario: EvaluationScenario,
    run_dir: Path,
    evaluation_run_id: str,
    sut: SeexrSutClient,
    judge: BinaryChecklistJudge,
    sut_semaphore: asyncio.Semaphore,
    evaluation_config: BinaryEvaluationConfig,
    stage_callback: Callable[[str, str], None] | None = None,
) -> str:
    paths = _case_paths(run_dir, scenario.case_id)
    paths["root"].mkdir(parents=True, exist_ok=True)
    if paths["result"].exists():
        return "skipped"

    stage = "sut"
    try:
        if stage_callback:
            stage_callback(scenario.case_id, stage)
        if paths["sut"].exists():
            sut_result = _load_sut(paths["sut"])
        else:
            request_id = str(
                uuid.uuid5(
                    AUTOMATED_RUN_NAMESPACE,
                    f"{evaluation_run_id}:{scenario.case_id}",
                )
            )
            async with sut_semaphore:
                sut_result = await sut.run_case(
                    scenario,
                    client_request_id=request_id,
                )
            atomic_write_json(
                paths["sut"],
                {
                    "case_id": sut_result.case_id,
                    "session_id": sut_result.session_id,
                    "run_id": sut_result.run_id,
                    "elapsed_ms": sut_result.elapsed_ms,
                    "create_run_attempts": sut_result.create_run_attempts,
                    "stream_reconnects": sut_result.stream_reconnects,
                    "retry_log": sut_result.retry_log,
                    # Auth recovery is a shared-client event in parallel mode;
                    # global counts are authoritative. This value is retained
                    # only as diagnostic context from the underlying call.
                    "auth_recoveries_observed": sut_result.auth_recoveries,
                    "request_message": build_sut_message(scenario),
                    "content": sut_result.content,
                    "events": sut_result.events,
                    "completed_at_utc": _utc_now(),
                },
            )

        stage = "parse"
        if stage_callback:
            stage_callback(scenario.case_id, stage)
        post_mode = post_improvement_mode_for_model_mode(sut.config.model_mode)
        if paths["parsed"].exists():
            payload = load_json(paths["parsed"])
            parsed = ParsedRiskAssessment.model_validate(payload["parsed"])
            deterministic = DeterministicAssessmentResult.model_validate(
                payload["deterministic"]
            )
            if deterministic.post_improvement_mode != post_mode:
                raise RuntimeError(
                    "Parsed checkpoint deterministic contract differs from current SUT mode"
                )
        else:
            parsed = parse_risk_assessment(sut_result.content)
            deterministic = evaluate_deterministic(
                parsed,
                post_improvement_mode=post_mode,
            )
            atomic_write_json(
                paths["parsed"],
                {
                    "parsed": parsed.model_dump(mode="json"),
                    "deterministic": deterministic.model_dump(mode="json"),
                    "completed_at_utc": _utc_now(),
                },
            )

        stage = "binary_judge"
        if stage_callback:
            stage_callback(scenario.case_id, stage)
        if paths["judge"].exists():
            payload = load_json(paths["judge"])
            evaluation = BinaryCaseEvaluation.model_validate(payload["evaluation"])
        else:
            evaluation = await evaluate_binary_case(
                judge=judge,
                scenario=scenario,
                generated=parsed.risks,
                config=evaluation_config,
            )
            atomic_write_json(
                paths["judge"],
                {
                    "evaluation": evaluation.model_dump(mode="json"),
                    "completed_at_utc": _utc_now(),
                },
            )

        stage = "result"
        if stage_callback:
            stage_callback(scenario.case_id, stage)
        atomic_write_json(
            paths["result"],
            {
                "protocol": "automated-kolas-v1",
                "status": "completed",
                "case_id": scenario.case_id,
                "source_rows": scenario.source_rows,
                "scenario_input": scenario.input.model_dump(mode="json"),
                "reference_count": len(scenario.references),
                "generated_count": len(parsed.risks),
                "sut": {
                    "session_id": sut_result.session_id,
                    "run_id": sut_result.run_id,
                    "elapsed_ms": sut_result.elapsed_ms,
                    "create_run_attempts": sut_result.create_run_attempts,
                    "stream_reconnects": sut_result.stream_reconnects,
                },
                "deterministic": deterministic.model_dump(mode="json"),
                "metrics": evaluation.metrics.model_dump(mode="json"),
                "match_count": len(evaluation.matches),
                "judge_call_count": len(evaluation.calls),
                "completed_at_utc": _utc_now(),
            },
        )
        paths["error"].unlink(missing_ok=True)
        return "completed"
    except Exception as exc:
        _save_error(
            paths["error"],
            scenario.case_id,
            stage,
            exc,
            sut_content=(
                sut_result.content
                if "sut_result" in locals()
                else None
            ),
        )
        raise


async def run_parallel_cases(
    *,
    scenarios: list[EvaluationScenario],
    run_dir: Path,
    evaluation_run_id: str,
    sut: SeexrSutClient,
    judge: BinaryChecklistJudge,
    config: ParallelRunnerConfig | None = None,
    continue_on_error: bool = True,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ParallelRunSummary:
    config = config or ParallelRunnerConfig.from_env()
    case_semaphore = asyncio.Semaphore(config.case_concurrency)
    sut_semaphore = asyncio.Semaphore(config.sut_concurrency)
    summary = ParallelRunSummary(selected=len(scenarios))
    stats_lock = asyncio.Lock()
    stages: dict[str, str] = {}

    def stage_callback(case_id: str, stage: str) -> None:
        stages[case_id] = stage
        if progress_callback:
            progress_callback(
                {
                    **summary.as_dict(),
                    "case_id": case_id,
                    "stage": stage,
                    "stages": dict(stages),
                }
            )

    async def run_one(scenario: EvaluationScenario) -> None:
        async with case_semaphore:
            async with stats_lock:
                summary.active += 1
            try:
                status = await process_automated_case(
                    scenario=scenario,
                    run_dir=run_dir,
                    evaluation_run_id=evaluation_run_id,
                    sut=sut,
                    judge=judge,
                    sut_semaphore=sut_semaphore,
                    evaluation_config=config.binary_config(),
                    stage_callback=stage_callback,
                )
                async with stats_lock:
                    if status == "skipped":
                        summary.skipped += 1
                    else:
                        summary.completed += 1
            except Exception:
                async with stats_lock:
                    summary.failed += 1
                if not continue_on_error:
                    raise
            finally:
                stages.pop(scenario.case_id, None)
                async with stats_lock:
                    summary.active -= 1
                if progress_callback:
                    progress_callback(
                        {
                            **summary.as_dict(),
                            "case_id": scenario.case_id,
                            "stage": "done",
                            "stages": dict(stages),
                        }
                    )

    tasks = [asyncio.create_task(run_one(scenario)) for scenario in scenarios]
    if continue_on_error:
        await asyncio.gather(*tasks, return_exceptions=False)
    else:
        try:
            await asyncio.gather(*tasks)
        except Exception:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
    return summary
