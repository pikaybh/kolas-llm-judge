from pathlib import Path

from kolas_llm_judge.automated_manifest import (
    capture_automated_method_identity,
    parallel_runner_identity,
)
from kolas_llm_judge.binary_judge import BinaryJudgeConfig
from kolas_llm_judge.parallel_runner import ParallelRunnerConfig
from kolas_llm_judge.sut_client import SutConfig


def test_automated_identity_binds_binary_judge_runner_sut_and_controls() -> None:
    root = Path.cwd()
    identity = capture_automated_method_identity(
        project_root=root,
        scenarios_path=root / "data/cases/scenarios_v1.jsonl",
        judge=BinaryJudgeConfig(),
        runner=ParallelRunnerConfig(),
        sut=SutConfig(model_mode="fast"),
    )
    assert identity["protocol"] == "automated-kolas-v1"
    assert identity["judge"]["pipeline_version"] == "binary-checklist-v1"
    assert identity["parallel_runner"]["case_concurrency"] == 24
    assert identity["sut_evaluation_identity"]["post_improvement_mode"] == "blank"
    assert identity["qualification_control_suite"]["control_count"] == 104
    assert len(identity["qualification_control_suite"]["sha256"]) == 64
    assert len(identity["official_runtime"]["sha256"]) == 64
    assert len(identity["source_tree_sha256"]) == 64


def test_parallel_runner_identity_changes_with_concurrency() -> None:
    first = parallel_runner_identity(ParallelRunnerConfig(case_concurrency=8))
    second = parallel_runner_identity(ParallelRunnerConfig(case_concurrency=4))
    assert first != second
