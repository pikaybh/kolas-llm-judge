from pathlib import Path

from kolas_llm_judge.official_runtime import (
    load_official_runtime,
    validate_official_runtime,
)
from kolas_llm_judge.sut_client import SutConfig


def test_frozen_official_runtime_has_benchmarked_concurrency() -> None:
    runtime = load_official_runtime()
    assert runtime.runtime_version == "official-runtime-v1"
    assert runtime.parallel.case_concurrency == 24
    assert runtime.parallel.sut_concurrency == 6
    assert runtime.judge.max_concurrency == 12
    assert runtime.judge.model == "gpt-5.6-sol"
    assert runtime.judge.reasoning_effort == "medium"
    assert runtime.qualification.control_count == 104
    assert runtime.metrics.primary_metric == "hazard_identification_accuracy"
    assert runtime.metrics.primary_rule_version == "hazard-identification-v1"
    assert runtime.metrics.primary_rule == "(same_hazard_mechanism AND context_compatible) OR accident_compatible"
    assert runtime.metrics.primary_denominator == (
        "references_with_completed_binary_match_matrix"
    )
    assert runtime.metrics.supplementary_kpi_metric == "hazard_semantic_identification_recall"
    assert runtime.metrics.supplementary_kpi_rule == (
        "same_hazard_mechanism AND context_compatible"
    )
    assert runtime.acceptance.sut_performance_decision == (
        "report_only_until_testing_lab_approval"
    )
    assert runtime.acceptance.performance_thresholds_frozen is False
    assert runtime.benchmark_evidence["fifty_case_wall_seconds"] == 255.38


def test_official_runtime_validates_frozen_dataset_and_ajqg() -> None:
    root = Path.cwd()
    runtime = validate_official_runtime(
        project_root=root,
        scenarios_path=root / "data/cases/scenarios_v1.jsonl",
    )
    assert runtime.dataset.dataset_id == "KOLAS_RA_GT"
    assert runtime.dataset.dataset_version == "1.0.0"
    assert runtime.dataset.schema_version == "kolas-ra-dataset-v1"
    assert runtime.dataset.source_rows == 843
    assert runtime.dataset.source_sha256 == (
        "b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a"
    )
    assert runtime.dataset.scenario_count == 425
    assert runtime.dataset.reference_count == 843


def test_official_sut_runtime_uses_env_only_for_credentials() -> None:
    runtime = load_official_runtime()
    env = SutConfig(
        base_url="https://evil.invalid/api",
        agent_id="wrong",
        token="secret-token",
        api_key="sk-test",
        email="eval@example.test",
        password="secret-password",
        risk_assessment_method="wrong",
        model_mode="expert",
        reasoning_style="creative",
        timeout_seconds=999,
        max_retries=99,
        retry_backoff_seconds=99,
    )
    frozen = runtime.sut_config_with_credentials(env)
    assert frozen.token is None
    assert frozen.email is None
    assert frozen.password is None
    assert frozen.base_url == "https://api.seexr.co.kr/api"
    assert frozen.agent_id == "risk-assessment"
    assert frozen.risk_assessment_method == "빈도강도법 5x4"
    assert frozen.model_mode == "fast"
    assert frozen.reasoning_style == "balanced"
    assert frozen.max_retries == 3


def test_official_runtime_rejects_tampered_binary_prompt(tmp_path: Path) -> None:
    import shutil
    import pytest

    root = Path.cwd()
    shutil.copytree(root / "src", tmp_path / "src")
    shutil.copy2(root / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copy2(root / "uv.lock", tmp_path / "uv.lock")
    for relative in [
        "configs/official_runtime_v1.yaml",
        "configs/ajqg_seed_v1.yaml",
        "configs/ajqg_gate_v1.yaml",
        "configs/rubric_binary_v1.yaml",
        "prompts/judge_binary_v1.md",
        "data/cases/scenarios_v1.jsonl",
        "data/cases/dataset_manifest.json",
        "data/raw/kolas_v7_73_test.csv.bz2",
    ]:
        source = root / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    prompt = tmp_path / "prompts/judge_binary_v1.md"
    prompt.write_text(
        prompt.read_text(encoding="utf-8") + "\nTAMPERED\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="artifact SHA mismatch"):
        validate_official_runtime(
            project_root=tmp_path,
            scenarios_path=tmp_path / "data/cases/scenarios_v1.jsonl",
        )


def test_official_runtime_rejects_tampered_raw_source(tmp_path: Path) -> None:
    import shutil
    import pytest

    root = Path.cwd()
    shutil.copytree(root / "src", tmp_path / "src")
    shutil.copy2(root / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copy2(root / "uv.lock", tmp_path / "uv.lock")
    for relative in [
        "configs/official_runtime_v1.yaml",
        "configs/ajqg_seed_v1.yaml",
        "configs/ajqg_gate_v1.yaml",
        "configs/rubric_binary_v1.yaml",
        "prompts/judge_binary_v1.md",
        "data/cases/scenarios_v1.jsonl",
        "data/cases/dataset_manifest.json",
        "data/raw/kolas_v7_73_test.csv.bz2",
    ]:
        source = root / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    raw = tmp_path / "data/raw/kolas_v7_73_test.csv.bz2"
    raw.write_bytes(raw.read_bytes() + b"TAMPER")
    with pytest.raises(RuntimeError, match="raw-source content SHA mismatch"):
        validate_official_runtime(
            project_root=tmp_path,
            scenarios_path=tmp_path / "data/cases/scenarios_v1.jsonl",
            runtime_path=tmp_path / "configs/official_runtime_v1.yaml",
        )


def test_official_runtime_requires_scoped_api_key() -> None:
    import pytest

    runtime = load_official_runtime()
    with pytest.raises(ValueError, match="SEEXR_API_KEY"):
        runtime.sut_config_with_credentials(
            SutConfig(email="legacy@example.test", password="legacy")
        )


def test_official_source_hash_is_cross_platform_and_tamper_sensitive(tmp_path: Path) -> None:
    from kolas_llm_judge.official_runtime import official_evaluator_source_sha256

    source = tmp_path / "src/kolas_llm_judge/fixture.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"first = 1\nsecond = 2\n")
    linux_sha = official_evaluator_source_sha256(tmp_path)
    source.write_bytes(b"first = 1\r\nsecond = 2\r\n")
    assert official_evaluator_source_sha256(tmp_path) == linux_sha
    source.write_bytes(b"first = 1\r\nsecond = 3\r\n")
    assert official_evaluator_source_sha256(tmp_path) != linux_sha
