"""Display-only HIA policy: no change to underlying metrics or sealed artifacts."""
import io
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

import kolas_llm_judge.cli as cli
from kolas_llm_judge.io_utils import load_json


def _capture(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr(cli, "console", Console(file=stream, width=160, color_system=None))
    return stream


def test_official_live_shows_hia_only_and_keeps_operational_status(monkeypatch, tmp_path: Path):
    stream = _capture(monkeypatch)
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    async def fake_execute(**kwargs):
        return SimpleNamespace(
            run_dir=run_dir,
            status="DEVELOPMENT_COMPLETE",
            procedure_valid=False,
            final_verification_ok=True,
            summary={
                "sut_completion_rate": {"rate": 0.7},
                "deterministic": {"schema_compliance": {"rate": 0.0}},
                "metrics": {
                    "hazard_identification_accuracy": {"rate": 1.0},
                    "hazard_semantic_identification_recall": {"rate": 0.7},
                    "reference_risk_coverage": {"rate": 0.6},
                },
            },
        )

    monkeypatch.setattr(cli, "execute_official_live", fake_execute)
    cli.official_live_command(
        case_limit=10,
        development=True,
        skip_qualification=True,
        case_concurrency=None,
        sut_concurrency=None,
    )
    output = stream.getvalue()
    assert "HIA (primary)" in output
    assert "100.00%" in output
    assert "Procedure valid" in output
    assert "Seal verified" in output
    assert "SUT completion" not in output
    assert "Semantic" not in output
    assert "Strict" not in output
    assert "Schema" not in output


def test_derived_hia_screen_retains_complete_json_artifact(monkeypatch, tmp_path: Path):
    stream = _capture(monkeypatch)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    output_path = tmp_path / "derived.json"
    source_analysis = {
        "source_run_id": "run",
        "coverage": {"dataset_references": 843},
        "metrics": {
            "hazard_identification_accuracy": {"rate": 0.83},
            "hazard_semantic_identification_recall": {"rate": 0.71},
            "strict_reference_risk_coverage_1to1": {"rate": 0.54},
        },
    }
    monkeypatch.setattr(cli, "derive_identification_analysis", lambda **kwargs: source_analysis)
    cli.derive_identification_command(run=str(run_dir), output=output_path)
    screen = stream.getvalue()
    assert "HIA (primary)" in screen and "83.00%" in screen
    assert "Secondary" not in screen and "Strict" not in screen
    assert "Dataset references" not in screen
    assert load_json(output_path) == source_analysis


def test_repeatability_screen_shows_only_hia_variability(monkeypatch, tmp_path: Path):
    stream = _capture(monkeypatch)
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    analysis = {
        "run_count": 2,
        "all_seals_verified": True,
        "aggregate_metric_stability": {
            "hazard_identification_accuracy": {"mean": 0.94, "range": 0.12},
            "hazard_semantic_identification_recall": {"mean": 0.66, "range": 0.2},
        },
        "semantic_reference_detection": {"stable_reference_rate": 0.77},
    }
    monkeypatch.setattr(cli, "compare_sut_repeatability", lambda paths: analysis)
    target = tmp_path / "repeatability.json"
    cli.compare_repeatability_command(runs=[str(a), str(b)], output=target)
    screen = stream.getvalue()
    assert "HIA (mean)" in screen and "94.00%" in screen
    assert "HIA (range)" in screen and "12.00%" in screen
    assert "Stable reference rate" not in screen
    assert "0.66" not in screen
    assert load_json(target) == analysis


def test_hia_display_handles_missing_rate_without_inventing_score():
    assert cli._format_hia(None) == "N/A"
    assert cli._format_hia({}) == "N/A"
    assert cli._format_hia({"rate": None}) == "N/A"
    assert cli._format_hia({"rate": 0.0}) == "0.00%"


def test_qualification_screen_keeps_gate_status_not_component_scores(monkeypatch, tmp_path: Path):
    stream = _capture(monkeypatch)

    async def fake_qualification(**kwargs):
        return SimpleNamespace(summary={
            "gate_pass": True,
            "checks": {"family_accuracy": {"value": 0.52, "minimum": 0.75, "pass": False}},
        })

    monkeypatch.setattr(cli, "run_qualification", fake_qualification)
    monkeypatch.setattr(cli, "write_qualification_artifacts",
                        lambda result, output: {"summary": tmp_path / "summary.json",
                                                "controls": tmp_path / "controls.csv"})
    cli.qualify_judge_command(output=tmp_path, repeats=2, require_pass=False)
    screen = stream.getvalue()
    assert "AJQG PASS" in screen
    assert "family_accuracy" not in screen
    assert "0.52" not in screen


def test_list_runs_shows_only_hia_as_performance_column(monkeypatch, tmp_path: Path):
    stream = _capture(monkeypatch)
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    run_dir = tmp_path / "runs" / "official-case"
    from kolas_llm_judge.io_utils import atomic_write_json
    atomic_write_json(run_dir / "manifest.json",
                      {"mode": "official-live", "selected_case_count": 10})
    atomic_write_json(run_dir / "completion.json", {"completed": 10})
    atomic_write_json(run_dir / "report/summary.json",
                      {"metrics": {"hazard_identification_accuracy": {"rate": 0.95},
                                   "hazard_semantic_identification_recall": {"rate": 0.3}}})
    cli.list_runs()
    screen = stream.getvalue()
    assert "HIA (primary)" in screen and "95.00%" in screen
    assert "Semantic" not in screen
    assert "30.00%" not in screen

def test_hia_uses_distinct_emphasized_color_in_every_monitor():
    from rich.table import Table

    label = cli._styled_hia("HIA (primary)")
    assert label.plain == "HIA (primary)"
    assert label.style == "bold bright_cyan"
    assert cli._styled_hia(cli._format_hia({"rate": 0.95})).plain == "95.00%"

    table = Table()
    table.add_column("Item")
    table.add_column("Value")
    cli._print_hia(table, {"hazard_identification_accuracy": {"rate": 0.95}})
    assert table.rows
    cells = table.columns
    assert cells[0]._cells[0].style == "bold bright_cyan"
    assert cells[1]._cells[0].style == "bold bright_cyan"
