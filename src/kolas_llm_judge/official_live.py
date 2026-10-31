from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from .automated_manifest import build_automated_manifest
from .automated_report import collect_automated_report, export_automated_report
from .binary_judge import BinaryChecklistJudge, BinaryJudgeConfig
from .doctor import run_doctor
from .io_utils import atomic_write_json, load_scenarios
from .manifest import capture_sut_api_contract, sut_api_contract_matches
from .official_runtime import validate_official_runtime
from .parallel_runner import ParallelRunnerConfig, run_parallel_cases
from .qualification import run_qualification, write_qualification_artifacts
from .qualification_controls import load_generated_control_suite
from .seal import seal_run, verify_run
from .sut_client import SeexrSutClient, SutConfig


@dataclass
class OfficialLiveResult:
    run_dir: Path
    status: str
    procedure_valid: bool
    development_mode: bool
    final_verification_ok: bool
    summary: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _development_instruction_only_failure(preflight: dict[str, Any], development: bool) -> bool:
    failed = [check["name"] for check in preflight.get("checks", []) if not check.get("ok")]
    return development and failed == ["evaluation_saved_instruction_empty"]


def make_official_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-official-live-{uuid.uuid4().hex[:8]}"


def _evenly_spaced_subset(items: list[Any], limit: int) -> list[Any]:
    if limit >= len(items):
        return list(items)
    if limit <= 0:
        return []
    if limit == 1:
        return [items[len(items) // 2]]
    indexes = [
        round(i * (len(items) - 1) / (limit - 1))
        for i in range(limit)
    ]
    return [items[index] for index in indexes]


def _phase(
    callback: Callable[[dict[str, Any]], None] | None,
    phase: str,
    **detail: Any,
) -> None:
    if callback:
        callback({"phase": phase, **detail})


async def execute_official_live(
    *,
    project_root: Path,
    scenarios_path: Path,
    run_id: str | None = None,
    case_limit: int | None = None,
    development_mode: bool = False,
    skip_qualification: bool = False,
    runner_config: ParallelRunnerConfig | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> OfficialLiveResult:
    if case_limit is not None and not development_mode:
        raise ValueError("case_limit is development-only; official mode must use all frozen scenarios")
    if skip_qualification and not development_mode:
        raise ValueError("skip_qualification is development-only")
    if runner_config is not None and not development_mode:
        raise ValueError("runner_config override is development-only")

    official_runtime = (
        validate_official_runtime(
            project_root=project_root,
            scenarios_path=scenarios_path,
        )
        if not development_mode
        else None
    )

    actual_run_id = run_id or make_official_run_id()
    run_dir = project_root / "runs" / actual_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()

    _phase(progress_callback, "preflight", status="running")
    preflight = await run_doctor(
        project_root=project_root,
        scenarios_path=scenarios_path,
        live=True,
        official=True,
    )
    failed_checks = [check for check in preflight["checks"] if not check["ok"]]
    # Smoke-only exception: never relax official KOLAS readiness or conceal the FAIL.
    development_instruction_exception = _development_instruction_only_failure(
        preflight, development_mode
    )
    if development_instruction_exception:
        preflight["development_exception"] = {
            "check": "evaluation_saved_instruction_empty",
            "reason": "Saved account instructions may influence smoke results; not official evidence.",
        }
    atomic_write_json(run_dir / "preflight.json", preflight)
    if not preflight.get("ok") and not development_instruction_exception:
        atomic_write_json(
            run_dir / "final_status.json",
            {
                "status": "INVALID_PREFLIGHT",
                "procedure_valid": False,
                "development_mode": development_mode,
                "completed_at_utc": _utc_now(),
            },
        )
        names = ", ".join(check["name"] for check in failed_checks)
        raise RuntimeError(
            f"Official-live preflight failed ({names}); see {run_dir / 'preflight.json'}"
        )
    _phase(
        progress_callback,
        "preflight",
        status="development-instructions-nonempty" if development_instruction_exception else "pass",
    )

    scenarios = load_scenarios(scenarios_path)
    selected = (
        _evenly_spaced_subset(scenarios, case_limit)
        if case_limit is not None
        else scenarios
    )
    if not selected:
        raise RuntimeError("No scenarios selected")

    env_sut_config = SutConfig.from_env()
    if official_runtime is not None:
        sut_config = official_runtime.sut_config_with_credentials(env_sut_config)
        judge_config = official_runtime.judge_config()
        runner_config = official_runtime.runner_config()
        qualification_repeats = official_runtime.qualification.repeats
    else:
        sut_config = env_sut_config
        judge_config = BinaryJudgeConfig.from_env()
        runner_config = runner_config or ParallelRunnerConfig.from_env()
        qualification_repeats = 2
    async with SeexrSutClient(sut_config) as api_client:
        api_start = capture_sut_api_contract(
            await api_client.healthcheck_auth(), sut_config
        )
    if not api_start.get("available"):
        raise RuntimeError("SUT API contract unavailable at start")


    judge = BinaryChecklistJudge(judge_config)
    qualification_dir = run_dir / "qualification"
    _phase(
        progress_callback,
        "qualification",
        status="running",
        controls=104,
    )
    if skip_qualification:
        suite = load_generated_control_suite(project_root / "configs/ajqg_seed_v1.yaml")
        qualification_summary = {
            "qualification_version": "ajqg-v1",
            "gate_version": "development-skip",
            "control_suite_sha256": suite.controls_sha256,
            "control_count": len(suite.controls),
            "judge": {
                "pipeline_version": judge_config.pipeline_version,
                "model": judge_config.model,
                "reasoning_effort": judge_config.reasoning_effort,
            },
            "gate_pass": True,
            "development_skip": True,
        }
        qualification_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(qualification_dir / "summary.json", qualification_summary)
        (qualification_dir / "control_results.csv").write_text(
            "development_skip\ntrue\n",
            encoding="utf-8",
        )
    else:
        qualification_result = await run_qualification(
            judge=judge,
            repeats=qualification_repeats,
        )
        write_qualification_artifacts(qualification_result, qualification_dir)
        qualification_summary = qualification_result.summary
    _phase(
        progress_callback,
        "qualification",
        status="pass" if qualification_summary.get("gate_pass") else "fail",
        gate_pass=bool(qualification_summary.get("gate_pass")),
    )

    manifest = build_automated_manifest(
        project_root=project_root,
        run_id=actual_run_id,
        scenarios_path=scenarios_path,
        selected_case_ids=[scenario.case_id for scenario in selected],
        judge=judge_config,
        runner=runner_config,
        sut=sut_config,
        qualification=qualification_summary,
        qualification_summary_path=qualification_dir / "summary.json",
        sut_api_start=api_start,
        development_mode=development_mode,
    )
    atomic_write_json(run_dir / "manifest.json", manifest)

    if not qualification_summary.get("gate_pass"):
        async with SeexrSutClient(sut_config) as api_client:
            api_end = capture_sut_api_contract(
                await api_client.healthcheck_auth(), sut_config
            )
        completion = {
            "status": "qualification_failed",
            "selected": len(selected),
            "processed": 0,
            "completed": 0,
            "failed": 0,
            "auth_recovery_count": 0,
            "sut_api_end": api_end,
            "sut_api_contract_stable": sut_api_contract_matches(api_start, api_end),
            "elapsed_ms": round((perf_counter() - started) * 1000),
            "completed_at_utc": _utc_now(),
        }
        atomic_write_json(run_dir / "completion.json", completion)
        export_automated_report(run_dir)
        atomic_write_json(
            run_dir / "final_status.json",
            {
                "status": "INVALID_QUALIFICATION",
                "procedure_valid": False,
                "development_mode": development_mode,
                "completed_at_utc": _utc_now(),
            },
        )
        seal_run(run_dir)
        first_verify = verify_run(run_dir)
        atomic_write_json(run_dir / "verification.json", first_verify)
        seal_run(run_dir)
        final_verify = verify_run(run_dir)
        await judge.client.close()
        return OfficialLiveResult(
            run_dir=run_dir,
            status="INVALID_QUALIFICATION",
            procedure_valid=False,
            development_mode=development_mode,
            final_verification_ok=bool(final_verify.get("ok")),
            summary=collect_automated_report(run_dir),
        )

    _phase(
        progress_callback,
        "evaluation",
        status="running",
        selected=len(selected),
    )
    sut = SeexrSutClient(sut_config)
    try:
        await sut.ensure_authenticated()

        def case_progress(payload: dict[str, Any]) -> None:
            _phase(progress_callback, "evaluation", status="running", **payload)

        run_summary = await run_parallel_cases(
            scenarios=selected,
            run_dir=run_dir,
            evaluation_run_id=actual_run_id,
            sut=sut,
            judge=judge,
            config=runner_config,
            continue_on_error=True,
            progress_callback=case_progress,
        )
        auth_recoveries = sut._auth_recovery_count
    finally:
        await sut.client.aclose()
        await judge.client.close()

    async with SeexrSutClient(sut_config) as api_client:
        api_end = capture_sut_api_contract(
            await api_client.healthcheck_auth(), sut_config
        )
    contract_stable = sut_api_contract_matches(api_start, api_end)
    completion = {
        "status": "completed",
        **run_summary.as_dict(),
        "auth_recovery_count": auth_recoveries,
        "sut_api_end": api_end,
        "sut_api_contract_stable": contract_stable,
        "elapsed_ms": round((perf_counter() - started) * 1000),
        "completed_at_utc": _utc_now(),
    }
    atomic_write_json(run_dir / "completion.json", completion)
    _phase(progress_callback, "evaluation", status="complete", **run_summary.as_dict())

    _phase(progress_callback, "report", status="running")
    export_automated_report(run_dir)
    report = collect_automated_report(run_dir)
    procedure_valid = bool(report.get("procedure_valid"))
    preliminary_status = (
        "DEVELOPMENT_COMPLETE"
        if development_mode
        else ("VALID" if procedure_valid else "INVALID")
    )
    atomic_write_json(
        run_dir / "final_status.json",
        {
            "status": preliminary_status,
            "procedure_valid": procedure_valid,
            "development_mode": development_mode,
            "seal_verified": None,
            "completed_at_utc": _utc_now(),
        },
    )
    _phase(progress_callback, "report", status="complete")

    _phase(progress_callback, "seal", status="running")
    first_seal = seal_run(run_dir)
    first_verify = verify_run(run_dir)
    atomic_write_json(
        run_dir / "verification.json",
        {
            "verification_of_initial_seal": first_verify,
            "initial_seal_root_sha256": first_seal.get("artifact_root_sha256"),
        },
    )
    atomic_write_json(
        run_dir / "final_status.json",
        {
            "status": preliminary_status,
            "procedure_valid": procedure_valid,
            "development_mode": development_mode,
            "seal_verified": bool(first_verify.get("ok")),
            "completed_at_utc": _utc_now(),
        },
    )
    final_seal = seal_run(run_dir)
    final_verify = verify_run(run_dir)
    final_ok = bool(final_verify.get("ok"))
    _phase(
        progress_callback,
        "seal",
        status="pass" if final_ok else "fail",
        root_sha256=final_seal.get("artifact_root_sha256"),
    )

    final_status = preliminary_status
    if not development_mode and (not procedure_valid or not final_ok):
        final_status = "INVALID"
    return OfficialLiveResult(
        run_dir=run_dir,
        status=final_status,
        procedure_valid=procedure_valid,
        development_mode=development_mode,
        final_verification_ok=final_ok,
        summary=report,
    )
