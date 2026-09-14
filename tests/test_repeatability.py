from pathlib import Path

from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.repeatability import compare_sut_repeatability
from kolas_llm_judge.seal import seal_run


def _make_run(root: Path, name: str, *, identified: bool) -> Path:
    run = root / name
    atomic_write_json(run / "manifest.json", {
        "run_id": name,
        "selected_case_ids": ["c1"],
        "dataset": {"sha256": "d" * 64},
        "method_identity": {"frozen": "same"},
        "sut_evaluation_identity": {"agent_id": "risk-assessment", "model_mode": "fast"},
    })
    atomic_write_json(run / "cases/c1/result.json", {
        "case_id": "c1",
        "metrics": {},
    })
    atomic_write_json(run / "cases/c1/binary_judge.json", {
        "evaluation": {
            "match_matrix": [{
                "reference_id": "r1",
                "generated_id": "g1",
                "same_hazard_mechanism": identified,
                "context_compatible": identified,
                "accident_compatible": True,
            }]
        }
    })
    seal_run(run)
    return run


def test_repeatability_tracks_strict_semantic_reference_detection(tmp_path: Path) -> None:
    a = _make_run(tmp_path, "a", identified=True)
    b = _make_run(tmp_path, "b", identified=False)
    result = compare_sut_repeatability([a, b])
    primary = result["aggregate_metric_stability"]["hazard_semantic_identification_recall"]
    assert primary["mean"] == 0.5
    assert primary["range"] == 1.0
    ref = result["semantic_reference_detection"]["per_reference"]["r1"]
    assert ref["detection_consistency"] == 0.5
    assert ref["stable_across_runs"] is False


def test_repeatability_rejects_different_frozen_identity(tmp_path: Path) -> None:
    import pytest
    a = _make_run(tmp_path, "a", identified=True)
    b = _make_run(tmp_path, "b", identified=True)
    manifest = __import__("json").loads((b / "manifest.json").read_text())
    manifest["method_identity"] = {"frozen": "different"}
    atomic_write_json(b / "manifest.json", manifest)
    seal_run(b)
    with pytest.raises(ValueError, match="same frozen"):
        compare_sut_repeatability([a, b])
