from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import sha256_file
from .deterministic import post_improvement_mode_for_model_mode
from .judge import JudgeConfig
from .sut_client import SutConfig


HASHED_PATHS = [
    Path("configs/evaluation.yaml"),
    Path("configs/rubric_v1.yaml"),
    Path("prompts/judge_v1.md"),
    Path("data/raw/PROVENANCE.md"),
    Path("data/cases/dataset_manifest.json"),
    Path("uv.lock"),
]

SOURCE_GLOBS = [
    "src/kolas_llm_judge/*.py",
    "configs/*.yaml",
    "prompts/*.md",
    "data/raw/PROVENANCE.md",
    "data/cases/dataset_manifest.json",
    "pyproject.toml",
    "uv.lock",
]



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(
    args: list[str],
    cwd: Path | None = None,
) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None




def capture_sut_api_contract(response: dict[str, Any], sut: SutConfig) -> dict[str, Any]:
    """Snapshot the *observable* API contract, not private server source code."""
    agents = response.get("agents")
    if not isinstance(agents, list):
        return {"available": False, "reason": "GET /agents returned no agents list"}
    details = sorted(
        ({"id": str(agent["id"]), "enabled": bool(agent.get("enabled", True))}
         for agent in agents if isinstance(agent, dict) and agent.get("id")),
        key=lambda item: item["id"],
    )
    if not any(row["id"] == sut.agent_id and row["enabled"] for row in details):
        return {"available": False, "reason": "risk-assessment agent not enabled"}
    observed = {"base_url": sut.base_url, "agent_id": sut.agent_id, "agents": details}
    digest = hashlib.sha256(json.dumps(observed, sort_keys=True).encode("utf-8")).hexdigest()
    return {"available": True, "base_url": sut.base_url, "agent_id": sut.agent_id,
            "api_contract_sha256": digest, "evidence": "authenticated GET /agents"}


def sut_api_contract_matches(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """Fail closed if either API contract observation is missing or changed."""
    return (
        isinstance(first, dict) and isinstance(second, dict)
        and first.get("available") is True and second.get("available") is True
        and isinstance(first.get("api_contract_sha256"), str)
        and first["api_contract_sha256"] == second.get("api_contract_sha256")
        and first.get("base_url") == second.get("base_url")
        and first.get("agent_id") == second.get("agent_id")
    )


def _source_tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    files: set[Path] = set()
    for pattern in SOURCE_GLOBS:
        files.update(
            path
            for path in root.glob(pattern)
            if path.is_file()
        )
    for path in sorted(
        files,
        key=lambda value: str(
            value.relative_to(root)
        ),
    ):
        relative = str(
            path.relative_to(root)
        ).replace("\\", "/")
        digest.update(
            relative.encode("utf-8")
        )
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _package_versions(
    names: list[str],
) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in names:
        try:
            result[name] = (
                importlib.metadata.version(name)
            )
        except (
            importlib.metadata.PackageNotFoundError
        ):
            result[name] = None
    return result



def sut_evaluation_identity(
    sut: SutConfig | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(sut, SutConfig):
        values = {
            "base_url": sut.base_url,
            "agent_id": sut.agent_id,
            "risk_assessment_method": sut.risk_assessment_method,
            "model_mode": sut.model_mode,
            "reasoning_style": sut.reasoning_style,
        }
    else:
        values = {
            key: sut.get(key)
            for key in (
                "base_url",
                "agent_id",
                "risk_assessment_method",
                "model_mode",
                "reasoning_style",
            )
        }
    model_mode = str(values.get("model_mode") or "")
    return {
        **values,
        "post_improvement_mode": (
            post_improvement_mode_for_model_mode(model_mode)
        ),
    }


def _judge_identity(judge: JudgeConfig) -> dict[str, Any]:
    return {
        "model": judge.model,
        "reasoning_effort": judge.reasoning_effort,
        "pipeline_version": judge.pipeline_version,
        "max_pairs_per_call": judge.max_pairs_per_call,
        "max_concurrency": judge.max_concurrency,
        "request_timeout_seconds": judge.request_timeout_seconds,
        "max_retries": judge.max_retries,
        "prompt_path": str(judge.prompt_path),
        "rubric_path": str(judge.rubric_path),
    }


def capture_current_method_identity(
    *,
    project_root: Path,
    scenarios_path: Path,
    judge: JudgeConfig,
) -> dict[str, Any]:
    artifacts: dict[str, str | None] = {}
    for relative in HASHED_PATHS:
        path = project_root / relative
        artifacts[str(relative)] = (
            sha256_file(path) if path.exists() else None
        )
    return {
        "dataset_sha256": sha256_file(scenarios_path),
        "evaluation_artifacts": artifacts,
        "source_tree_sha256": _source_tree_hash(project_root),
        "judge": _judge_identity(judge),
    }


def method_identity_from_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    identity = manifest.get("method_identity")
    if isinstance(identity, dict):
        return identity
    dataset = manifest.get("dataset")
    artifacts = manifest.get("evaluation_artifacts")
    judge = manifest.get("judge")
    source_tree = manifest.get("source_tree_sha256")
    if not (
        isinstance(dataset, dict)
        and isinstance(artifacts, dict)
        and isinstance(judge, dict)
        and isinstance(source_tree, str)
    ):
        return None
    return {
        "dataset_sha256": dataset.get("sha256"),
        "evaluation_artifacts": artifacts,
        "source_tree_sha256": source_tree,
        "judge": judge,
    }


def method_identity_matches(
    first: dict[str, Any] | None,
    second: dict[str, Any] | None,
) -> bool:
    return (
        isinstance(first, dict)
        and isinstance(second, dict)
        and first == second
    )

def build_run_manifest(
    *,
    project_root: Path,
    run_id: str,
    mode: str,
    scenarios_path: Path,
    selected_case_ids: list[str],
    sut: SutConfig,
    judge: JudgeConfig,
    calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    method_identity = capture_current_method_identity(
        project_root=project_root,
        scenarios_path=scenarios_path,
        judge=judge,
    )
    files = method_identity["evaluation_artifacts"]

    git_head = _git(
        ["rev-parse", "HEAD"],
        cwd=project_root,
    )
    git_status = _git(
        ["status", "--porcelain"],
        cwd=project_root,
    )

    return {
        "manifest_version": "1.2",
        "created_at_utc": _utc_now(),
        "run_id": run_id,
        "mode": mode,
        "selected_case_count": len(
            selected_case_ids
        ),
        "selected_case_ids": selected_case_ids,
        "dataset": {
            "path": str(scenarios_path),
            "sha256": sha256_file(
                scenarios_path
            ),
        },
        "evaluation_artifacts": files,
        "source_tree_sha256": method_identity["source_tree_sha256"],
        "method_identity": method_identity,
        "git": {
            "head": git_head,
            "dirty": bool(git_status),
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": _package_versions(
                [
                    "pydantic",
                    "httpx",
                    "openai",
                    "scipy",
                    "numpy",
                    "pandas",
                    "typer",
                    "rich",
                    "scikit-learn",
                ]
            ),
        },
        "sut_evaluation_identity": sut_evaluation_identity(sut),
        "sut": {
            "base_url": sut.base_url,
            "agent_id": sut.agent_id,
            "risk_assessment_method": (
                sut.risk_assessment_method
            ),
            "model_mode": sut.model_mode,
            "reasoning_style": (
                sut.reasoning_style
            ),
            "timeout_seconds": (
                sut.timeout_seconds
            ),
            "max_retries": sut.max_retries,
            "retry_backoff_seconds": sut.retry_backoff_seconds,
            "auth_mode": sut.auth_mode,
        },
        "judge": _judge_identity(judge),
        "calibration": calibration,
        "secrets_recorded": False,
    }


def write_manifest_once(
    path: Path,
    manifest: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    payload = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    try:
        with path.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as f:
            f.write(payload)
            f.flush()
    except FileExistsError:
        existing = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        immutable_keys = [
            "run_id",
            "mode",
            "selected_case_ids",
            "selection",
            "dataset",
            "evaluation_artifacts",
            "source_tree_sha256",
            "method_identity",
            "sut_evaluation_identity",
            "sut",
            "judge",
            "calibration",
        ]
        mismatched = [
            key
            for key in immutable_keys
            if existing.get(key)
            != manifest.get(key)
        ]
        if mismatched:
            raise RuntimeError(
                "Existing manifest does not "
                "match current run configuration: "
                f"{mismatched}"
            )
