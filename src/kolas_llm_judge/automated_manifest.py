from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .binary_judge import BinaryJudgeConfig
from .dataset import sha256_file
from .parallel_runner import ParallelRunnerConfig
from .qualification_controls import load_generated_control_suite
from .sut_client import SutConfig
from .manifest import sut_evaluation_identity


AUTOMATED_HASHED_PATHS = [
    Path("configs/ajqg_seed_v1.yaml"),
    Path("configs/ajqg_gate_v1.yaml"),
    Path("configs/rubric_binary_v1.yaml"),
    Path("prompts/judge_binary_v1.md"),
    Path("docs/automated_kolas_protocol_v1.md"),
    Path("data/raw/PROVENANCE.md"),
    Path("data/cases/dataset_manifest.json"),
    Path("pyproject.toml"),
    Path("uv.lock"),
]

AUTOMATED_SOURCE_GLOBS = [
    "src/kolas_llm_judge/*.py",
    "configs/*.yaml",
    "prompts/*.md",
    "docs/*.md",
    "data/raw/PROVENANCE.md",
    "data/cases/dataset_manifest.json",
    "pyproject.toml",
    "uv.lock",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def automated_source_tree_sha256(project_root: Path) -> str:
    files: set[Path] = set()
    for pattern in AUTOMATED_SOURCE_GLOBS:
        files.update(path for path in project_root.glob(pattern) if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda p: str(p.relative_to(project_root))):
        relative = str(path.relative_to(project_root)).replace("\\", "/")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def automated_judge_identity(config: BinaryJudgeConfig) -> dict[str, Any]:
    return {
        "pipeline_version": config.pipeline_version,
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "max_concurrency": config.max_concurrency,
        "request_timeout_seconds": config.request_timeout_seconds,
        "max_retries": config.max_retries,
        "prompt_path": str(config.prompt_path),
        "rubric_path": str(config.rubric_path),
    }


def parallel_runner_identity(config: ParallelRunnerConfig) -> dict[str, Any]:
    return {
        "case_concurrency": config.case_concurrency,
        "sut_concurrency": config.sut_concurrency,
        "match_chunk_size": config.match_chunk_size,
        "quality_chunk_size": config.quality_chunk_size,
        "safety_chunk_size": config.safety_chunk_size,
    }


def capture_automated_method_identity(
    *,
    project_root: Path,
    scenarios_path: Path,
    judge: BinaryJudgeConfig,
    runner: ParallelRunnerConfig,
    sut: SutConfig,
) -> dict[str, Any]:
    suite = load_generated_control_suite(project_root / "configs/ajqg_seed_v1.yaml")
    artifacts: dict[str, str | None] = {}
    for relative in AUTOMATED_HASHED_PATHS:
        path = project_root / relative
        artifacts[str(relative)] = sha256_file(path) if path.exists() else None
    return {
        "protocol": "automated-kolas-v1",
        "dataset_sha256": sha256_file(scenarios_path),
        "source_tree_sha256": automated_source_tree_sha256(project_root),
        "evaluation_artifacts": artifacts,
        "judge": automated_judge_identity(judge),
        "parallel_runner": parallel_runner_identity(runner),
        "sut_evaluation_identity": sut_evaluation_identity(sut),
        "qualification_control_suite": {
            "suite_version": suite.suite_version,
            "control_count": len(suite.controls),
            "sha256": suite.controls_sha256,
        },
    }


def build_automated_manifest(
    *,
    project_root: Path,
    run_id: str,
    scenarios_path: Path,
    selected_case_ids: list[str],
    judge: BinaryJudgeConfig,
    runner: ParallelRunnerConfig,
    sut: SutConfig,
    qualification: dict[str, Any],
    qualification_summary_path: Path,
    sut_source_start: dict[str, Any],
    development_mode: bool,
) -> dict[str, Any]:
    git_head = _git(["rev-parse", "HEAD"], project_root)
    git_status = _git(["status", "--porcelain"], project_root) or ""
    return {
        "manifest_version": "automated-1.0",
        "created_at_utc": _utc_now(),
        "protocol": "automated-kolas-v1",
        "run_id": run_id,
        "mode": "official-live" if not development_mode else "official-live-development",
        "development_mode": development_mode,
        "selected_case_count": len(selected_case_ids),
        "selected_case_ids": selected_case_ids,
        "dataset": {
            "path": str(scenarios_path),
            "sha256": sha256_file(scenarios_path),
        },
        "git": {
            "head": git_head,
            "dirty": bool(git_status.strip()),
            "status_sha256": hashlib.sha256(git_status.encode("utf-8")).hexdigest(),
        },
        "method_identity": capture_automated_method_identity(
            project_root=project_root,
            scenarios_path=scenarios_path,
            judge=judge,
            runner=runner,
            sut=sut,
        ),
        "sut_evaluation_identity": sut_evaluation_identity(sut),
        "sut_source_start": sut_source_start,
        "qualification": {
            "gate_pass": bool(qualification.get("gate_pass")),
            "qualification_version": qualification.get("qualification_version"),
            "gate_version": qualification.get("gate_version"),
            "control_suite_sha256": qualification.get("control_suite_sha256"),
            "control_count": qualification.get("control_count"),
            "judge": qualification.get("judge"),
            "summary_path": str(qualification_summary_path),
            "summary_sha256": sha256_file(qualification_summary_path),
        },
        "parallel_runner": parallel_runner_identity(runner),
        "binary_judge": automated_judge_identity(judge),
    }
