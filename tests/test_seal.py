from __future__ import annotations

from pathlib import Path

from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.seal import seal_run, verify_run


def _make_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "runs/run-test"
    run_dir.mkdir(parents=True)
    atomic_write_json(
        run_dir / "manifest.json",
        {
            "run_id": "run-test",
            "mode": "full",
            "git": {
                "head": "commit-test",
                "dirty": False,
            },
        },
    )
    atomic_write_json(
        run_dir / "completion.json",
        {
            "run_id": "run-test",
            "sut_source_stable": True,
        },
    )
    case_dir = run_dir / "cases/case-1"
    case_dir.mkdir(parents=True)
    atomic_write_json(
        case_dir / "result.json",
        {
            "case_id": "case-1",
            "status": "completed",
        },
    )
    return run_dir


def test_seal_and_verify_run(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    seal = seal_run(run_dir)
    assert seal["artifact_count"] == 3
    assert len(
        seal["artifact_root_sha256"]
    ) == 64

    result = verify_run(run_dir)
    assert result["ok"] is True
    assert result["missing"] == []
    assert result["mismatched"] == []
    assert result["unexpected"] == []


def test_verify_detects_tampering_and_reseal_chains(
    tmp_path: Path,
) -> None:
    run_dir = _make_run(tmp_path)
    first = seal_run(run_dir)

    result_path = (
        run_dir / "cases/case-1/result.json"
    )
    atomic_write_json(
        result_path,
        {
            "case_id": "case-1",
            "status": "tampered",
        },
    )
    broken = verify_run(run_dir)
    assert broken["ok"] is False
    assert [
        row["path"]
        for row in broken["mismatched"]
    ] == ["cases/case-1/result.json"]

    second = seal_run(run_dir)
    assert (
        second["previous_seal_sha256"]
        is not None
    )
    assert (
        second["artifact_root_sha256"]
        != first["artifact_root_sha256"]
    )
    repaired = verify_run(run_dir)
    assert repaired["ok"] is True


def test_verify_detects_unexpected_artifact(
    tmp_path: Path,
) -> None:
    run_dir = _make_run(tmp_path)
    seal_run(run_dir)
    (run_dir / "extra.txt").write_text(
        "unexpected",
        encoding="utf-8",
    )
    result = verify_run(run_dir)
    assert result["ok"] is False
    assert result["unexpected"] == [
        "extra.txt"
    ]
