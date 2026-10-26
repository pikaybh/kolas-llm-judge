from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import replace
import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from .binary_human_calibration import (
    make_binary_human_calibration_template,
    score_binary_human_calibration,
)
from .calibration import (
    make_human_calibration_template,
    run_judge_repeatability,
    score_human_calibration,
)
from .dataset import import_dataset
from .derived_analysis import derive_identification_analysis
from .doctor import run_doctor
from .io_utils import atomic_write_json
from .qualification import run_qualification, write_qualification_artifacts
from .official_live import execute_official_live
from .parallel_runner import ParallelRunnerConfig
from .report import export_reports
from .repeatability import compare_sut_repeatability
from .runner import execute_run
from .seal import seal_run, verify_run

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIOS = PROJECT_ROOT / "data/cases/scenarios_v1.jsonl"

load_dotenv(PROJECT_ROOT / ".env")

app = typer.Typer(
    no_args_is_help=True,
    help="SEEXR KOLAS LLM-as-Judge evaluation harness",
)
console = Console()


def _resolve_run_dir(run: str) -> Path:
    candidate = Path(run)
    if candidate.exists():
        return candidate.resolve()
    run_dir = PROJECT_ROOT / "runs" / run
    if not run_dir.exists():
        raise typer.BadParameter(f"Run not found: {run}")
    return run_dir


@app.command("import-dataset")
def import_dataset_command(
    source: Path = typer.Option(
        PROJECT_ROOT / "data/raw/kolas_v7_73_test.csv.bz2",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(DEFAULT_SCENARIOS),
    manifest: Path = typer.Option(
        PROJECT_ROOT / "data/cases/dataset_manifest.json"
    ),
    expected_rows: int = typer.Option(843),
    expected_scenarios: int = typer.Option(425),
) -> None:
    result = import_dataset(
        source,
        output,
        manifest,
        expected_rows=expected_rows,
        expected_scenarios=expected_scenarios,
    )
    table = Table(title="Dataset import complete")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Source rows", str(result.source_rows))
    table.add_row("Scenarios", str(result.scenario_count))
    table.add_row("References", str(result.reference_count))
    table.add_row("Source SHA-256", result.source_sha256)
    table.add_row("Cases SHA-256", result.cases_sha256)
    console.print(table)


@app.command("doctor")
def doctor_command(
    live: bool = typer.Option(
        False,
        help="Also authenticate against the live SEEXR API.",
    ),
    official: bool = typer.Option(
        False,
        help="Also require a committed, clean evaluation harness.",
    ),
    require_ready: bool = typer.Option(
        False,
        help="Exit non-zero if any readiness check fails.",
    ),
) -> None:
    result = asyncio.run(
        run_doctor(
            project_root=PROJECT_ROOT,
            scenarios_path=DEFAULT_SCENARIOS,
            live=live,
            official=official,
        )
    )
    table = Table(title="KOLAS preflight")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in result["checks"]:
        table.add_row(
            check["name"],
            "[green]PASS[/green]" if check["ok"] else "[red]FAIL[/red]",
            str(check["detail"]),
        )
    console.print(table)
    if result.get("warnings"):
        warning_table = Table(title="Warnings")
        warning_table.add_column("Warning")
        warning_table.add_column("Detail")
        for warning in result["warnings"]:
            warning_table.add_row(
                warning["name"],
                str(warning["detail"]),
            )
        console.print(warning_table)
    console.print(
        "[green]READY[/green]" if result["ok"] else "[yellow]NOT READY[/yellow]"
    )
    if require_ready and not result["ok"]:
        raise typer.Exit(code=2)


@app.command("qualify-judge")
def qualify_judge_command(
    output: Path | None = typer.Option(
        None,
        help="Qualification artifact directory. Defaults to runs/_qualification/<UTC timestamp>.",
    ),
    repeats: int = typer.Option(2, min=2, max=5),
    require_pass: bool = typer.Option(
        True,
        help="Exit non-zero when the automatic Judge qualification gate fails.",
    ),
) -> None:
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = PROJECT_ROOT / "runs" / "_qualification" / stamp
    result = asyncio.run(
        run_qualification(
            repeats=repeats,
        )
    )
    paths = write_qualification_artifacts(result, output)
    table = Table(title="Automatic Judge Qualification Gate")
    table.add_column("Check")
    table.add_column("Value")
    table.add_column("Minimum")
    table.add_column("Status")
    for name, check in result.summary["checks"].items():
        if name == "required_families":
            table.add_row(
                name,
                ", ".join(check["value"]),
                "all",
                "[green]PASS[/green]" if check["pass"] else "[red]FAIL[/red]",
            )
            continue
        value = check.get("value")
        minimum = check.get("minimum")
        table.add_row(
            name,
            f"{value:.4f}" if isinstance(value, float) else str(value),
            f"{minimum:.4f}" if isinstance(minimum, float) else str(minimum),
            "[green]PASS[/green]" if check["pass"] else "[red]FAIL[/red]",
        )
    console.print(table)
    console.print(f"summary: {paths['summary']}")
    console.print(f"controls: {paths['controls']}")
    console.print(
        "[green]AJQG PASS[/green]"
        if result.summary["gate_pass"]
        else "[red]AJQG FAIL[/red]"
    )
    if require_pass and not result.summary["gate_pass"]:
        raise typer.Exit(code=5)


@app.command("run")
def run_command(
    mode: str = typer.Option(
        "smoke",
        help="smoke (10), pilot (50), or full (425)",
    ),
    run_id: str | None = typer.Option(
        None,
        help="Reuse an existing run id to resume checkpoints.",
    ),
    smoke_cases: int = typer.Option(10, min=1),
    pilot_cases: int = typer.Option(50, min=1),
    stop_on_error: bool = typer.Option(
        False,
        help="Abort on the first failed case instead of checkpointing and continuing.",
    ),
    calibration_run: str | None = typer.Option(
        None,
        help="Run containing calibration/gate_result.json. Required for full.",
    ),
    allow_uncalibrated_full: bool = typer.Option(
        False,
        help="Development override only. Never use for an official candidate run.",
    ),
) -> None:
    calibration_gate = None
    if calibration_run:
        calibration_gate = (
            _resolve_run_dir(calibration_run)
            / "calibration/gate_result.json"
        )
        if not calibration_gate.exists():
            raise typer.BadParameter(
                f"Calibration gate result not found: {calibration_gate}"
            )

    run_dir = asyncio.run(
        execute_run(
            project_root=PROJECT_ROOT,
            scenarios_path=DEFAULT_SCENARIOS,
            mode=mode,
            run_id=run_id,
            smoke_cases=smoke_cases,
            pilot_cases=pilot_cases,
            continue_on_error=not stop_on_error,
            calibration_gate_path=calibration_gate,
            allow_uncalibrated_full=allow_uncalibrated_full,
        )
    )
    console.print(f"[green]Run finished:[/green] {run_dir}")


@app.command("report")
def report_command(
    run: str = typer.Argument(..., help="Run id or run directory"),
) -> None:
    run_dir = _resolve_run_dir(run)
    paths = export_reports(run_dir)
    table = Table(title="Report exported")
    table.add_column("Artifact")
    table.add_column("Path")
    for name, path in paths.items():
        table.add_row(name, str(path))
    console.print(table)


@app.command("make-binary-calibration")
def make_binary_calibration_command(
    run: str = typer.Argument(..., help="Completed official-live pilot/full run id"),
    match_sample_size: int = typer.Option(150, min=1),
    quality_sample_size: int = typer.Option(100, min=1),
    safety_sample_size: int = typer.Option(100, min=1),
    seed: int = typer.Option(20260914),
    output_dir: Path | None = typer.Option(
        None,
        help="Derived output directory. Defaults outside the sealed run tree.",
    ),
) -> None:
    """Create blinded expert-label templates for the official Boolean Rubric."""
    run_dir = _resolve_run_dir(run)
    output_dir = output_dir or (PROJECT_ROOT / "derived/binary_calibration" / run_dir.name)
    paths = make_binary_human_calibration_template(
        run_dir=run_dir,
        scenarios_path=DEFAULT_SCENARIOS,
        output_dir=output_dir,
        match_sample_size=match_sample_size,
        quality_sample_size=quality_sample_size,
        safety_sample_size=safety_sample_size,
        seed=seed,
    )
    for name, path in paths.items():
        console.print(f"{name}: {path}")


@app.command("score-binary-calibration")
def score_binary_calibration_command(
    run: str = typer.Argument(..., help="Official-live run id containing filled binary calibration CSVs"),
    directory: Path | None = typer.Option(
        None,
        help="Derived calibration directory. Defaults outside the sealed run tree.",
    ),
) -> None:
    """Compare blinded expert consensus against persisted official Boolean Judge decisions."""
    run_dir = _resolve_run_dir(run)
    directory = directory or (PROJECT_ROOT / "derived/binary_calibration" / run_dir.name)
    result = score_binary_human_calibration(
        run_dir=run_dir,
        match_csv=directory / "human_binary_match.csv",
        quality_csv=directory / "human_binary_quality.csv",
        safety_csv=directory / "human_binary_safety.csv",
    )
    output = directory / "gate_result.json"
    atomic_write_json(output, result)
    console.print_json(json=json.dumps(result, ensure_ascii=False))
    console.print("[green]BINARY HUMAN CALIBRATION PASS[/green]" if result["gate_pass"] else "[red]BINARY HUMAN CALIBRATION FAIL[/red]")
    if not result["gate_pass"]:
        raise typer.Exit(code=3)


@app.command("make-calibration")
def make_calibration_command(
    run: str = typer.Argument(..., help="Completed pilot/full run id"),
    sample_size: int = typer.Option(150, min=10),
    quality_sample_size: int | None = typer.Option(
        None,
        min=10,
        help="Matched-quality pair sample size. Defaults to sample-size.",
    ),
    generated_sample_size: int | None = typer.Option(
        None,
        min=10,
        help="Generated-risk sample size. Defaults to sample-size.",
    ),
    seed: int = typer.Option(20260908),
) -> None:
    run_dir = _resolve_run_dir(run)
    output_dir = run_dir / "calibration"
    paths = make_human_calibration_template(
        run_dir=run_dir,
        scenarios_path=DEFAULT_SCENARIOS,
        output_dir=output_dir,
        sample_size=sample_size,
        quality_sample_size=quality_sample_size,
        generated_sample_size=generated_sample_size,
        seed=seed,
    )
    for name, path in paths.items():
        console.print(f"{name}: {path}")


@app.command("judge-repeatability")
def judge_repeatability_command(
    run: str = typer.Argument(..., help="Completed pilot/full run id"),
    repeats: int = typer.Option(3, min=2),
    max_cases: int = typer.Option(20, min=1),
) -> None:
    run_dir = _resolve_run_dir(run)
    output_dir = run_dir / "calibration/repeatability"
    summary = asyncio.run(
        run_judge_repeatability(
            run_dir=run_dir,
            scenarios_path=DEFAULT_SCENARIOS,
            output_dir=output_dir,
            project_root=PROJECT_ROOT,
            repeats=repeats,
            max_cases=max_cases,
        )
    )
    console.print_json(json=json.dumps(summary, ensure_ascii=False))


@app.command("score-calibration")
def score_calibration_command(
    run: str = typer.Argument(..., help="Completed pilot/full run id"),
    labeled_pairs: Path | None = typer.Option(
        None,
        help="Filled human_pairs.csv. Defaults to run calibration directory.",
    ),
    labeled_quality_pairs: Path | None = typer.Option(
        None,
        help="Filled human_quality_pairs.csv. Defaults to run calibration directory.",
    ),
    labeled_generated: Path | None = typer.Option(
        None,
        help="Filled human_generated.csv. Defaults to run calibration directory.",
    ),
) -> None:
    run_dir = _resolve_run_dir(run)
    pairs = labeled_pairs or run_dir / "calibration/human_pairs.csv"
    quality_pairs = (
        labeled_quality_pairs
        or run_dir / "calibration/human_quality_pairs.csv"
    )
    generated = (
        labeled_generated
        or run_dir / "calibration/human_generated.csv"
    )
    repeatability = run_dir / "calibration/repeatability/summary.json"
    result = score_human_calibration(
        run_dir=run_dir,
        labeled_pairs_csv=pairs,
        labeled_quality_pairs_csv=quality_pairs,
        labeled_generated_csv=generated,
        repeatability_summary=repeatability,
    )
    output = run_dir / "calibration/gate_result.json"
    atomic_write_json(output, result)
    console.print_json(json=json.dumps(result, ensure_ascii=False))
    console.print(
        "[green]CALIBRATION GATE PASS[/green]"
        if result["gate_pass"]
        else "[red]CALIBRATION GATE FAIL[/red]"
    )
    if not result["gate_pass"]:
        raise typer.Exit(code=3)


@app.command("official-live")
def official_live_command(
    case_limit: int | None = typer.Option(
        None,
        min=1,
        help="Development-only case limit. Omit for the official 425-case run.",
    ),
    development: bool = typer.Option(
        False,
        help="Development/benchmark mode. Required when using --case-limit or --skip-qualification.",
    ),
    skip_qualification: bool = typer.Option(
        False,
        help="Development-only: skip live AJQG to benchmark case throughput.",
    ),
    case_concurrency: int | None = typer.Option(None, min=1),
    sut_concurrency: int | None = typer.Option(None, min=1),
) -> None:
    if case_limit is not None and not development:
        raise typer.BadParameter("--case-limit requires --development")
    if skip_qualification and not development:
        raise typer.BadParameter("--skip-qualification requires --development")
    if (case_concurrency is not None or sut_concurrency is not None) and not development:
        raise typer.BadParameter(
            "concurrency overrides require --development; official mode uses frozen runtime"
        )

    runner = None
    if development:
        runner = ParallelRunnerConfig.from_env()
        if case_concurrency is not None:
            runner = replace(runner, case_concurrency=case_concurrency)
        if sut_concurrency is not None:
            runner = replace(runner, sut_concurrency=sut_concurrency)

    expected_total = case_limit or 425
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.fields[phase]}[/bold]"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn("ok={task.fields[ok]} fail={task.fields[fail]} active={task.fields[active]}"),
        TextColumn("{task.fields[stages]}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "official-live",
            total=expected_total,
            phase="PREPARING",
            ok=0,
            fail=0,
            active=0,
            stages="",
        )

        def on_progress(payload: dict[str, object]) -> None:
            phase = str(payload.get("phase") or "").upper()
            status = str(payload.get("status") or "")
            if phase != "EVALUATION":
                progress.update(
                    task,
                    phase=f"{phase} {status}".strip(),
                )
                return
            total = int(payload.get("selected") or expected_total)
            completed = int(payload.get("completed") or 0)
            failed = int(payload.get("failed") or 0)
            skipped = int(payload.get("skipped") or 0)
            processed = int(payload.get("processed") or (completed + failed + skipped))
            active = int(payload.get("active") or 0)
            stage_map = payload.get("stages")
            counts = Counter(
                str(value)
                for value in (stage_map.values() if isinstance(stage_map, dict) else [])
            )
            stage_text = " ".join(
                f"{name}={count}"
                for name, count in sorted(counts.items())
            )
            progress.update(
                task,
                total=total,
                completed=processed,
                phase=f"EVALUATION {status}".strip(),
                ok=completed + skipped,
                fail=failed,
                active=active,
                stages=stage_text,
            )

        result = asyncio.run(
            execute_official_live(
                project_root=PROJECT_ROOT,
                scenarios_path=DEFAULT_SCENARIOS,
                case_limit=case_limit,
                development_mode=development,
                skip_qualification=skip_qualification,
                runner_config=runner,
                progress_callback=on_progress,
            )
        )

    summary = result.summary
    table = Table(title="Automated KOLAS Live Result")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Status", result.status)
    table.add_row("Run", result.run_dir.name)
    table.add_row("Procedure valid", str(result.procedure_valid))
    table.add_row("Seal verified", str(result.final_verification_ok))
    table.add_row(
        "SUT completion",
        str((summary.get("sut_completion_rate") or {}).get("rate")),
    )
    table.add_row(
        "Secondary strict semantic recall",
        str(
            (summary.get("metrics") or {})
            .get("hazard_semantic_identification_recall", {})
            .get("rate")
        ),
    )
    table.add_row(
        "Proposed primary HIA",
        str(
            (summary.get("metrics") or {})
            .get("hazard_identification_accuracy", {})
            .get("rate")
        ),
    )
    table.add_row(
        "Strict reference coverage",
        str((summary.get("metrics") or {}).get("reference_risk_coverage", {}).get("rate")),
    )
    table.add_row(
        "Schema compliance",
        str((summary.get("deterministic") or {}).get("schema_compliance", {}).get("rate")),
    )
    console.print(table)
    console.print(f"Artifacts: {result.run_dir}")
    if not development and result.status != "VALID":
        raise typer.Exit(code=6)


@app.command("derive-identification")
def derive_identification_command(
    run: str = typer.Argument(..., help="Run id or run directory"),
    output: Path | None = typer.Option(
        None,
        help="Output JSON path; defaults to derived/<run>-identification.json",
    ),
) -> None:
    """Recompute identification metrics from persisted Judge logs without new LLM calls."""
    run_dir = _resolve_run_dir(run)
    analysis = derive_identification_analysis(
        run_dir=run_dir,
        scenarios_path=DEFAULT_SCENARIOS,
    )
    if output is None:
        output = PROJECT_ROOT / "derived" / f"{run_dir.name}-identification.json"
    atomic_write_json(output, analysis)

    metrics = analysis.get("metrics") or {}
    coverage = analysis.get("coverage") or {}
    table = Table(title="Derived Hazard Identification Analysis")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Source run", str(analysis.get("source_run_id")))
    table.add_row(
        "Secondary strict semantic recall",
        str((metrics.get("hazard_semantic_identification_recall") or {}).get("rate")),
    )
    table.add_row(
        "Proposed primary HIA",
        str((metrics.get("hazard_identification_accuracy") or {}).get("rate")),
    )
    table.add_row(
        "Strict reference coverage (1:1)",
        str((metrics.get("strict_reference_risk_coverage_1to1") or {}).get("rate")),
    )
    table.add_row(
        "Semantic evaluable references",
        str(coverage.get("semantic_evaluable_references")),
    )
    table.add_row("Dataset references", str(coverage.get("dataset_references")))
    table.add_row(
        "End-to-end if unjudged are failures",
        str(
            (
                metrics.get(
                    "end_to_end_hazard_identification_if_unjudged_are_failures"
                )
                or {}
            ).get("rate")
        ),
    )
    console.print(table)
    console.print(f"Derived artifact: {output}")


@app.command("compare-repeatability")
def compare_repeatability_command(
    runs: list[str] = typer.Argument(..., help="Two or more equivalent sealed run ids/directories"),
    output: Path | None = typer.Option(None, help="Output JSON path"),
) -> None:
    """Compare repeated live SUT runs under the same frozen test identity."""
    run_dirs = [_resolve_run_dir(run) for run in runs]
    analysis = compare_sut_repeatability(run_dirs)
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = PROJECT_ROOT / "derived" / f"repeatability-{stamp}.json"
    atomic_write_json(output, analysis)
    primary = (analysis.get("aggregate_metric_stability") or {}).get(
        "hazard_semantic_identification_recall", {}
    )
    detection = analysis.get("semantic_reference_detection") or {}
    table = Table(title="SUT Semantic Repeatability")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Runs", str(analysis.get("run_count")))
    table.add_row("All seals verified", str(analysis.get("all_seals_verified")))
    table.add_row("Primary metric mean", str(primary.get("mean")))
    table.add_row("Primary metric std", str(primary.get("std")))
    table.add_row("Primary metric range", str(primary.get("range")))
    table.add_row("Stable reference rate", str(detection.get("stable_reference_rate")))
    console.print(table)
    console.print(f"Repeatability artifact: {output}")


@app.command("seal")
def seal_command(
    run: str = typer.Argument(..., help="Run id or run directory"),
) -> None:
    run_dir = _resolve_run_dir(run)
    seal = seal_run(run_dir)
    console.print(
        f"[green]SEALED[/green] {seal['artifact_root_sha256']} "
        f"({seal['artifact_count']} artifacts)"
    )


@app.command("verify")
def verify_command(
    run: str = typer.Argument(..., help="Run id or run directory"),
) -> None:
    run_dir = _resolve_run_dir(run)
    result = verify_run(run_dir)
    console.print_json(json=json.dumps(result, ensure_ascii=False))
    if not result.get("ok"):
        raise typer.Exit(code=4)


@app.command("show-manifest")
def show_manifest(
    manifest: Path = typer.Option(
        PROJECT_ROOT / "data/cases/dataset_manifest.json"
    ),
) -> None:
    console.print_json(json=manifest.read_text(encoding="utf-8"))


@app.command("list-runs")
def list_runs() -> None:
    runs_dir = PROJECT_ROOT / "runs"
    table = Table(title="Evaluation runs")
    table.add_column("Run")
    table.add_column("Mode")
    table.add_column("Selected")
    table.add_column("Completion")
    for run_dir in sorted(
        (path for path in runs_dir.iterdir() if path.is_dir()),
        reverse=True,
    ):
        manifest = run_dir / "manifest.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        completion = run_dir / "completion.json"
        table.add_row(
            run_dir.name,
            str(data.get("mode", "")),
            str(data.get("selected_case_count", "")),
            "yes" if completion.exists() else "no",
        )
    console.print(table)


def main() -> None:
    app()
