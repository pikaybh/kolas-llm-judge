from __future__ import annotations

import asyncio
import json
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .dataset import sha256_file
from .deterministic import evaluate_deterministic
from .io_utils import atomic_write_json, load_json, load_scenarios
from .judge import JudgeCallRecord, JudgeConfig, LlmJudge
from .manifest import (
    build_run_manifest,
    capture_current_method_identity,
    capture_sut_source_fingerprints,
    method_identity_matches,
    sut_source_matches,
    write_manifest_once,
)
from .matching import match_risks
from .metrics import calculate_case_metrics
from .models import CaseJudgeResult, DeterministicAssessmentResult, EvaluationScenario, ParsedRiskAssessment
from .parser import parse_risk_assessment
from .report import export_reports
from .sut_client import SeexrSutClient, SutConfig, SutRunResult, build_sut_message

console = Console()
RUN_NAMESPACE = uuid.UUID("6d20c7eb-2901-4af4-b8a1-a0f62e389a8e")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_run_id(mode: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{mode}-{uuid.uuid4().hex[:8]}"


def select_cases(
    scenarios: list[EvaluationScenario],
    *,
    mode: str,
    smoke_cases: int = 10,
    pilot_cases: int = 50,
) -> list[EvaluationScenario]:
    if mode == "full":
        return list(scenarios)
    limit = smoke_cases if mode == "smoke" else pilot_cases
    limit = min(limit, len(scenarios))
    if limit <= 0:
        return []

    # Evenly sample the full ordered dataset rather than taking only the first rows.
    if limit == 1:
        return [scenarios[len(scenarios) // 2]]
    indexes = {
        round(i * (len(scenarios) - 1) / (limit - 1))
        for i in range(limit)
    }
    selected = [scenarios[index] for index in sorted(indexes)]
    if len(selected) < limit:
        used = {case.case_id for case in selected}
        for scenario in scenarios:
            if scenario.case_id not in used:
                selected.append(scenario)
                used.add(scenario.case_id)
            if len(selected) == limit:
                break
    return selected[:limit]


def _checkpoint_paths(run_dir: Path, case_id: str) -> dict[str, Path]:
    root = run_dir / "cases" / case_id
    return {
        "root": root,
        "sut": root / "sut.json",
        "parsed": root / "parsed.json",
        "judge": root / "judge.json",
        "result": root / "result.json",
        "error": root / "error.json",
    }


def _save_error(path: Path, case_id: str, stage: str, exc: BaseException) -> None:
    atomic_write_json(
        path,
        {
            "case_id": case_id,
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=20),
            "updated_at_utc": utc_now(),
        },
    )


def _load_sut(path: Path) -> SutRunResult:
    payload = load_json(path)
    return SutRunResult(
        case_id=payload["case_id"],
        session_id=payload["session_id"],
        run_id=payload["run_id"],
        content=payload["content"],
        elapsed_ms=int(payload["elapsed_ms"]),
        events=payload.get("events", []),
    )


async def process_case(
    *,
    scenario: EvaluationScenario,
    run_dir: Path,
    evaluation_run_id: str,
    sut: SeexrSutClient,
    judge: LlmJudge,
    match_threshold: int = 3,
) -> str:
    paths = _checkpoint_paths(run_dir, scenario.case_id)
    paths["root"].mkdir(parents=True, exist_ok=True)

    if paths["result"].exists():
        return "skipped"

    stage = "sut"
    try:
        if paths["sut"].exists():
            sut_result = _load_sut(paths["sut"])
        else:
            client_request_id = str(
                uuid.uuid5(RUN_NAMESPACE, f"{evaluation_run_id}:{scenario.case_id}")
            )
            sut_result = await sut.run_case(
                scenario,
                client_request_id=client_request_id,
            )
            atomic_write_json(
                paths["sut"],
                {
                    "case_id": sut_result.case_id,
                    "session_id": sut_result.session_id,
                    "run_id": sut_result.run_id,
                    "elapsed_ms": sut_result.elapsed_ms,
                    "request_message": build_sut_message(scenario),
                    "content": sut_result.content,
                    "events": sut_result.events,
                    "completed_at_utc": utc_now(),
                },
            )

        stage = "parse"
        if paths["parsed"].exists():
            parsed_payload = load_json(paths["parsed"])
            parsed = ParsedRiskAssessment.model_validate(parsed_payload["parsed"])
            deterministic = DeterministicAssessmentResult.model_validate(
                parsed_payload["deterministic"]
            )
        else:
            parsed = parse_risk_assessment(sut_result.content)
            deterministic = evaluate_deterministic(parsed)
            atomic_write_json(
                paths["parsed"],
                {
                    "parsed": parsed.model_dump(mode="json"),
                    "deterministic": deterministic.model_dump(mode="json"),
                    "completed_at_utc": utc_now(),
                },
            )

        stage = "judge"
        if paths["judge"].exists():
            judge_payload = load_json(paths["judge"])
            judge_result = CaseJudgeResult.model_validate(judge_payload["result"])
            judge_record = JudgeCallRecord(
                result=judge_result,
                response_id=judge_payload.get("response_id"),
                response_model=judge_payload.get("response_model"),
                usage=judge_payload.get("usage"),
                calls=judge_payload.get("calls"),
            )
        else:
            judge_record = await judge.evaluate_case(scenario, parsed.risks)
            atomic_write_json(
                paths["judge"],
                {
                    "result": judge_record.result.model_dump(mode="json"),
                    "response_id": judge_record.response_id,
                    "response_model": judge_record.response_model,
                    "usage": judge_record.usage,
                    "calls": judge_record.calls,
                    "completed_at_utc": utc_now(),
                },
            )

        stage = "matching"
        matches = match_risks(
            scenario,
            parsed.risks,
            judge_record.result,
            threshold=match_threshold,
        )
        metrics = calculate_case_metrics(
            scenario,
            parsed.risks,
            judge_record.result,
            matches,
        )

        atomic_write_json(
            paths["result"],
            {
                "status": "completed",
                "case_id": scenario.case_id,
                "source_rows": scenario.source_rows,
                "scenario_input": scenario.input.model_dump(mode="json"),
                "reference_count": len(scenario.references),
                "sut": {
                    "session_id": sut_result.session_id,
                    "run_id": sut_result.run_id,
                    "elapsed_ms": sut_result.elapsed_ms,
                },
                "parsed": parsed.model_dump(mode="json"),
                "deterministic": deterministic.model_dump(mode="json"),
                "judge": {
                    "response_id": judge_record.response_id,
                    "response_model": judge_record.response_model,
                    "usage": judge_record.usage,
                    "calls": judge_record.calls,
                },
                "matches": [match.model_dump(mode="json") for match in matches],
                "metrics": metrics.model_dump(mode="json"),
                "completed_at_utc": utc_now(),
            },
        )
        paths["error"].unlink(missing_ok=True)
        return "completed"
    except Exception as exc:
        _save_error(paths["error"], scenario.case_id, stage, exc)
        raise


async def execute_run(
    *,
    project_root: Path,
    scenarios_path: Path,
    mode: str,
    run_id: str | None = None,
    smoke_cases: int = 10,
    pilot_cases: int = 50,
    continue_on_error: bool = True,
    calibration_gate_path: Path | None = None,
    allow_uncalibrated_full: bool = False,
) -> Path:
    if mode not in {"smoke", "pilot", "full"}:
        raise ValueError("mode must be smoke, pilot, or full")

    calibration: dict[str, Any] | None = None
    gate_data: dict[str, Any] | None = None
    if calibration_gate_path is not None:
        gate_data = load_json(calibration_gate_path)
        frozen_method = gate_data.get("frozen_method")
        calibration = {
            "gate_path": str(calibration_gate_path),
            "gate_sha256": sha256_file(calibration_gate_path),
            "gate_pass": bool(gate_data.get("gate_pass")),
            "source_run_id": (
                frozen_method.get("source_run_id")
                if isinstance(frozen_method, dict)
                else None
            ),
            "method_identity_match": None,
        }
    if mode == "full" and not allow_uncalibrated_full:
        if calibration is None:
            raise RuntimeError(
                "Full run requires a passed calibration gate. "
                "Provide --calibration-run, or explicitly use "
                "--allow-uncalibrated-full for development only."
            )
        if not calibration["gate_pass"]:
            raise RuntimeError(
                "Calibration gate did not pass; full run is blocked."
            )

    scenarios = load_scenarios(scenarios_path)
    selected = select_cases(
        scenarios,
        mode=mode,
        smoke_cases=smoke_cases,
        pilot_cases=pilot_cases,
    )
    actual_run_id = run_id or make_run_id(mode)
    run_dir = project_root / "runs" / actual_run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    sut_config = SutConfig.from_env()
    judge_config = JudgeConfig.from_env()

    current_method_identity = capture_current_method_identity(
        project_root=project_root,
        scenarios_path=scenarios_path,
        judge=judge_config,
    )
    if calibration is not None and gate_data is not None:
        frozen_method = gate_data.get("frozen_method")
        frozen_identity = (
            frozen_method.get("method_identity")
            if isinstance(frozen_method, dict)
            else None
        )
        identity_match = method_identity_matches(
            frozen_identity,
            current_method_identity,
        )
        calibration["method_identity_match"] = identity_match
        if (
            mode == "full"
            and not allow_uncalibrated_full
            and not identity_match
        ):
            raise RuntimeError(
                "Current evaluation/Judge method differs from the "
                "calibrated frozen method; full run is blocked."
            )

    manifest = build_run_manifest(
        project_root=project_root,
        run_id=actual_run_id,
        mode=mode,
        scenarios_path=scenarios_path,
        selected_case_ids=[case.case_id for case in selected],
        sut=sut_config,
        judge=judge_config,
        calibration=calibration,
    )
    write_manifest_once(run_dir / "manifest.json", manifest)

    async with SeexrSutClient(sut_config) as sut:
        await sut.ensure_authenticated()
        judge = LlmJudge(judge_config)
        completed = 0
        failed = 0
        skipped = 0
        with Progress(
            TextColumn("[bold]KOLAS[/bold] {task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(mode, total=len(selected))
            for scenario in selected:
                try:
                    status = await process_case(
                        scenario=scenario,
                        run_dir=run_dir,
                        evaluation_run_id=actual_run_id,
                        sut=sut,
                        judge=judge,
                    )
                    if status == "skipped":
                        skipped += 1
                    else:
                        completed += 1
                except Exception as exc:
                    failed += 1
                    progress.console.print(
                        f"[red]{scenario.case_id} failed:[/red] {type(exc).__name__}: {exc}"
                    )
                    if not continue_on_error:
                        raise
                finally:
                    progress.advance(task)

    end_sut_source = capture_sut_source_fingerprints()
    sut_source_stable = sut_source_matches(
        manifest["sut_source"],
        end_sut_source,
    )
    completion_payload = {
        "run_id": actual_run_id,
        "completed_at_utc": utc_now(),
        "completed_this_invocation": completed,
        "failed_this_invocation": failed,
        "skipped_this_invocation": skipped,
        "sut_source_stable": sut_source_stable,
        "sut_source_at_end": end_sut_source,
    }
    atomic_write_json(run_dir / "completion.json", completion_payload)
    reports = export_reports(run_dir)
    completion_payload["report_files"] = {
        key: str(value) for key, value in reports.items()
    }
    atomic_write_json(run_dir / "completion.json", completion_payload)
    if not sut_source_stable:
        raise RuntimeError(
            "Production SUT source changed during the evaluation run; "
            "the run is not valid as an official candidate."
        )
    return run_dir
