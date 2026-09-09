from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from .binary_judge import BinaryJudgeConfig
from .dataset import sha256_file
from .identification import (
    HAZARD_IDENTIFICATION_DENOMINATOR,
    HAZARD_IDENTIFICATION_RULE,
    HAZARD_IDENTIFICATION_RULE_VERSION,
)
from .io_utils import load_json, load_scenarios
from .parallel_runner import ParallelRunnerConfig
from .qualification_controls import load_generated_control_suite
from .sut_client import SutConfig, _normalize_base_url


DEFAULT_OFFICIAL_RUNTIME_PATH = Path("configs/official_runtime_v1.yaml")

FROZEN_EVALUATOR_SOURCE_GLOBS = (
    "src/kolas_llm_judge/*.py",
    "pyproject.toml",
    "uv.lock",
)


def official_evaluator_source_sha256(project_root: Path) -> str:
    files: set[Path] = set()
    for pattern in FROZEN_EVALUATOR_SOURCE_GLOBS:
        files.update(path for path in project_root.glob(pattern) if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda p: str(p.relative_to(project_root))):
        relative = str(path.relative_to(project_root)).replace("\\", "/")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class FrozenDatasetConfig(BaseModel):
    scenario_count: int = Field(gt=0)
    reference_count: int = Field(gt=0)
    scenarios_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenQualificationConfig(BaseModel):
    seed_path: str
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gate_path: str
    gate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_suite_version: str
    control_count: int = Field(gt=0)
    control_suite_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    repeats: int = Field(ge=2, le=5)


class FrozenJudgeConfig(BaseModel):
    pipeline_version: str
    model: str
    reasoning_effort: str
    max_concurrency: int = Field(gt=0)
    request_timeout_seconds: float = Field(ge=30.0)
    max_retries: int = Field(ge=0)
    prompt_path: str
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_path: str
    rubric_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenMetricPolicy(BaseModel):
    hazard_identification_rule_version: str
    hazard_identification_rule: str
    hazard_identification_denominator: str


class FrozenParallelConfig(BaseModel):
    case_concurrency: int = Field(gt=0)
    sut_concurrency: int = Field(gt=0)
    match_chunk_size: int = Field(gt=0)
    quality_chunk_size: int = Field(gt=0)
    safety_chunk_size: int = Field(gt=0)


class FrozenSutConfig(BaseModel):
    base_url: str
    agent_id: str
    risk_assessment_method: str
    model_mode: str
    reasoning_style: str
    timeout_seconds: float = Field(gt=0)
    max_retries: int = Field(ge=0)
    retry_backoff_seconds: float = Field(ge=0)


class OfficialRuntimeConfig(BaseModel):
    runtime_version: str
    protocol: str
    evaluator_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset: FrozenDatasetConfig
    qualification: FrozenQualificationConfig
    judge: FrozenJudgeConfig
    metrics: FrozenMetricPolicy
    parallel: FrozenParallelConfig
    sut: FrozenSutConfig
    benchmark_evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_versions(self) -> "OfficialRuntimeConfig":
        if self.runtime_version != "official-runtime-v1":
            raise ValueError("Unsupported official runtime version")
        if self.protocol != "automated-kolas-v1":
            raise ValueError("Official runtime protocol mismatch")
        if self.judge.pipeline_version != "binary-checklist-v1":
            raise ValueError("Official runtime requires binary-checklist-v1")
        if self.qualification.control_suite_version != "ajqg-controls-v1":
            raise ValueError("Official runtime AJQG suite version mismatch")
        if (
            self.metrics.hazard_identification_rule_version
            != HAZARD_IDENTIFICATION_RULE_VERSION
        ):
            raise ValueError("Official runtime hazard-identification version mismatch")
        if self.metrics.hazard_identification_rule != HAZARD_IDENTIFICATION_RULE:
            raise ValueError("Official runtime hazard-identification rule mismatch")
        if (
            self.metrics.hazard_identification_denominator
            != HAZARD_IDENTIFICATION_DENOMINATOR
        ):
            raise ValueError("Official runtime hazard-identification denominator mismatch")
        return self

    def judge_config(self) -> BinaryJudgeConfig:
        return BinaryJudgeConfig(
            model=self.judge.model,
            reasoning_effort=self.judge.reasoning_effort,
            max_concurrency=self.judge.max_concurrency,
            request_timeout_seconds=self.judge.request_timeout_seconds,
            max_retries=self.judge.max_retries,
            pipeline_version=self.judge.pipeline_version,
            prompt_path=Path(self.judge.prompt_path),
            rubric_path=Path(self.judge.rubric_path),
        )

    def runner_config(self) -> ParallelRunnerConfig:
        return ParallelRunnerConfig(
            case_concurrency=self.parallel.case_concurrency,
            sut_concurrency=self.parallel.sut_concurrency,
            match_chunk_size=self.parallel.match_chunk_size,
            quality_chunk_size=self.parallel.quality_chunk_size,
            safety_chunk_size=self.parallel.safety_chunk_size,
        )

    def sut_config_with_credentials(self, env_config: SutConfig) -> SutConfig:
        return SutConfig(
            base_url=_normalize_base_url(self.sut.base_url),
            agent_id=self.sut.agent_id,
            token=env_config.token,
            email=env_config.email,
            password=env_config.password,
            risk_assessment_method=self.sut.risk_assessment_method,
            model_mode=self.sut.model_mode,
            reasoning_style=self.sut.reasoning_style,
            timeout_seconds=self.sut.timeout_seconds,
            max_retries=self.sut.max_retries,
            retry_backoff_seconds=self.sut.retry_backoff_seconds,
        )


def load_official_runtime(
    path: Path = DEFAULT_OFFICIAL_RUNTIME_PATH,
) -> OfficialRuntimeConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return OfficialRuntimeConfig.model_validate(payload)


def validate_official_runtime(
    *,
    project_root: Path,
    scenarios_path: Path,
    runtime_path: Path = DEFAULT_OFFICIAL_RUNTIME_PATH,
) -> OfficialRuntimeConfig:
    absolute_runtime = (
        runtime_path
        if runtime_path.is_absolute()
        else project_root / runtime_path
    )
    runtime = load_official_runtime(absolute_runtime)

    actual_source_sha = official_evaluator_source_sha256(project_root)
    if actual_source_sha != runtime.evaluator_source_sha256:
        raise RuntimeError(
            "Frozen official evaluator source SHA mismatch: "
            f"expected={runtime.evaluator_source_sha256}, actual={actual_source_sha}"
        )

    actual_dataset_sha = sha256_file(scenarios_path)
    if actual_dataset_sha != runtime.dataset.scenarios_sha256:
        raise RuntimeError(
            "Frozen official dataset SHA mismatch: "
            f"expected={runtime.dataset.scenarios_sha256}, actual={actual_dataset_sha}"
        )
    scenarios = load_scenarios(scenarios_path)
    if len(scenarios) != runtime.dataset.scenario_count:
        raise RuntimeError(
            "Frozen official scenario count mismatch: "
            f"expected={runtime.dataset.scenario_count}, actual={len(scenarios)}"
        )
    dataset_manifest_path = project_root / "data/cases/dataset_manifest.json"
    dataset_manifest = load_json(dataset_manifest_path)
    if int(dataset_manifest.get("reference_count") or 0) != runtime.dataset.reference_count:
        raise RuntimeError(
            "Frozen official reference count mismatch: "
            f"expected={runtime.dataset.reference_count}, "
            f"actual={dataset_manifest.get('reference_count')}"
        )

    frozen_files = (
        (runtime.qualification.seed_path, runtime.qualification.seed_sha256),
        (runtime.qualification.gate_path, runtime.qualification.gate_sha256),
        (runtime.judge.prompt_path, runtime.judge.prompt_sha256),
        (runtime.judge.rubric_path, runtime.judge.rubric_sha256),
    )
    for relative, expected_sha in frozen_files:
        artifact = project_root / relative
        if not artifact.is_file():
            raise RuntimeError(f"Frozen official artifact missing: {relative}")
        actual_sha = sha256_file(artifact)
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Frozen official artifact SHA mismatch for {relative}: "
                f"expected={expected_sha}, actual={actual_sha}"
            )

    suite = load_generated_control_suite(project_root / runtime.qualification.seed_path)
    if suite.suite_version != runtime.qualification.control_suite_version:
        raise RuntimeError("Frozen official AJQG suite version mismatch")
    if len(suite.controls) != runtime.qualification.control_count:
        raise RuntimeError("Frozen official AJQG control count mismatch")
    if suite.controls_sha256 != runtime.qualification.control_suite_sha256:
        raise RuntimeError(
            "Frozen official AJQG SHA mismatch: "
            f"expected={runtime.qualification.control_suite_sha256}, "
            f"actual={suite.controls_sha256}"
        )
    return runtime
