from pathlib import Path

from kolas_llm_judge.automated_manifest import (
    capture_automated_method_identity,
    parallel_runner_identity,
)
from kolas_llm_judge.binary_judge import BinaryJudgeConfig
from kolas_llm_judge.parallel_runner import ParallelRunnerConfig
from kolas_llm_judge.sut_client import SutConfig


def test_automated_identity_binds_binary_judge_runner_sut_without_ajqg() -> None:
    root = Path.cwd()
    identity = capture_automated_method_identity(
        project_root=root,
        scenarios_path=root / "data/cases/scenarios_v1.jsonl",
        judge=BinaryJudgeConfig(),
        runner=ParallelRunnerConfig(),
        sut=SutConfig(model_mode="fast"),
    )
    assert identity["protocol"] == "automated-kolas-v2"
    assert identity["judge"]["pipeline_version"] == "binary-checklist-v1"
    assert identity["parallel_runner"]["case_concurrency"] == 24
    assert identity["sut_evaluation_identity"]["post_improvement_mode"] == "blank"
    assert "qualification_control_suite" not in identity
    assert "independent_judge_validation" in identity
    assert len(identity["official_runtime"]["sha256"]) == 64
    assert len(identity["source_tree_sha256"]) == 64


def test_parallel_runner_identity_changes_with_concurrency() -> None:
    first = parallel_runner_identity(ParallelRunnerConfig(case_concurrency=8))
    second = parallel_runner_identity(ParallelRunnerConfig(case_concurrency=4))
    assert first != second

def test_v2_automated_manifest_has_no_qualification_gate(tmp_path: Path) -> None:
    from kolas_llm_judge.automated_manifest import build_automated_manifest
    from kolas_llm_judge.io_utils import atomic_write_json
    from kolas_llm_judge.sut_client import SutConfig

    scenario_path = tmp_path / "scenarios.jsonl"
    scenario_path.write_text('{"id":"fixture"}\n', encoding="utf-8")
    # Only fingerprinted inputs, no AJQG configs or internal docs.
    for rel in [
        "configs/official_runtime_v2.yaml",
        "configs/rubric_binary_v1.yaml",
        "prompts/judge_binary_v1.md",
        "data/raw/PROVENANCE.md",
        "data/cases/dataset_manifest.json",
        "pyproject.toml",
        "uv.lock",
    ]:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    manifest = build_automated_manifest(
        project_root=tmp_path,
        run_id="v2-fixture",
        scenarios_path=scenario_path,
        selected_case_ids=["case-1"],
        judge=BinaryJudgeConfig(),
        runner=ParallelRunnerConfig(),
        sut=SutConfig(model_mode="fast"),
        qualification=None,
        qualification_summary_path=None,
        sut_api_start={"available": True},
        development_mode=False,
    )
    assert manifest["protocol"] == "automated-kolas-v2"
    assert manifest["qualification"]["gate_pass"] is None
    assert manifest["qualification"]["summary_path"] is None
    assert manifest["official_runtime"]["path"] == "configs/official_runtime_v2.yaml"
    assert all("ajqg" not in name.lower() for name in manifest["method_identity"]["evaluation_artifacts"])
