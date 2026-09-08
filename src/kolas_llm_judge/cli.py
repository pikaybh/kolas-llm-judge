from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .calibration import (
    make_human_calibration_template,
    run_judge_repeatability,
    score_human_calibration,
)
from .dataset import import_dataset
from .doctor import run_doctor
from .io_utils import atomic_write_json
from .report import export_reports
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


@app.command("make-calibration")
def make_calibration_command(
    run: str = typer.Argument(..., help="Completed pilot/full run id"),
    sample_size: int = typer.Option(150, min=10),
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
    labeled_generated: Path | None = typer.Option(
        None,
        help="Filled human_generated.csv. Defaults to run calibration directory.",
    ),
) -> None:
    run_dir = _resolve_run_dir(run)
    pairs = labeled_pairs or run_dir / "calibration/human_pairs.csv"
    generated = (
        labeled_generated
        or run_dir / "calibration/human_generated.csv"
    )
    repeatability = run_dir / "calibration/repeatability/summary.json"
    result = score_human_calibration(
        run_dir=run_dir,
        labeled_pairs_csv=pairs,
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
