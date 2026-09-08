from __future__ import annotations

import fnmatch
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
from .judge import JudgeConfig
from .sut_client import SutConfig


HASHED_PATHS = [
    Path("configs/evaluation.yaml"),
    Path("configs/rubric_v1.yaml"),
    Path("prompts/judge_v1.md"),
    Path("docs/evaluation_spec.md"),
    Path("data/raw/PROVENANCE.md"),
    Path("data/cases/dataset_manifest.json"),
    Path("uv.lock"),
]

SOURCE_GLOBS = [
    "src/kolas_llm_judge/*.py",
    "configs/*.yaml",
    "prompts/*.md",
    "docs/*.md",
    "data/raw/PROVENANCE.md",
    "data/cases/dataset_manifest.json",
    "pyproject.toml",
    "uv.lock",
]

CORE_RELEVANT_GLOBS = [
    "package.json",
    "package-lock.json",
    "tsconfig*.json",
    "src/main.ts",
    "src/app.module.ts",
    "src/common/**/*.ts",
    "src/modules/agents/**/*.ts",
    "src/modules/chat/**/*.ts",
    "src/modules/auth/**/*.ts",
    "src/modules/users/**/*.ts",
]

AGENTS_RELEVANT_GLOBS = [
    "package.json",
    "package-lock.json",
    "tsconfig*.json",
    "src/mastra/**/*.ts",
    "src/mastra/**/*.json",
    "src/mastra/**/*.yaml",
    "src/mastra/**/*.yml",
]

AGENTS_EXCLUDED_PREFIXES = [
    "src/mastra/public/.mastra/",
    "src/mastra/node_modules/",
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


def _matches_any(
    relative_path: str,
    patterns: list[str],
) -> bool:
    normalized = relative_path.replace("\\", "/")
    return any(
        fnmatch.fnmatch(normalized, pattern)
        for pattern in patterns
    )


def _is_excluded(
    relative_path: str,
    prefixes: list[str],
) -> bool:
    normalized = relative_path.replace("\\", "/")
    return any(
        normalized.startswith(prefix)
        for prefix in prefixes
    )


def _status_path(line: str) -> str | None:
    if len(line) < 4:
        return None
    value = line[3:].strip()
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value or None


def _relevant_source_fingerprint(
    repo: Path,
    *,
    patterns: list[str],
    excluded_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    excluded_prefixes = excluded_prefixes or []
    if not (repo / ".git").exists():
        return {
            "path": str(repo),
            "available": False,
        }

    head = _git(
        ["rev-parse", "HEAD"],
        cwd=repo,
    )
    status = (
        _git(
            ["status", "--porcelain=v1"],
            cwd=repo,
        )
        or ""
    )
    status_lines = [
        line
        for line in status.splitlines()
        if line.strip()
    ]

    files: set[Path] = set()
    for pattern in patterns:
        for path in repo.glob(pattern):
            if not path.is_file():
                continue
            relative = str(
                path.relative_to(repo)
            ).replace("\\", "/")
            if _is_excluded(
                relative,
                excluded_prefixes,
            ):
                continue
            files.add(path)

    relevant_status: list[str] = []
    for line in status_lines:
        relative = _status_path(line)
        if relative is None:
            continue
        if _is_excluded(
            relative,
            excluded_prefixes,
        ):
            continue
        if _matches_any(relative, patterns):
            relevant_status.append(line)

    digest = hashlib.sha256()
    for path in sorted(
        files,
        key=lambda value: str(
            value.relative_to(repo)
        ),
    ):
        relative = str(
            path.relative_to(repo)
        ).replace("\\", "/")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")

    # Include relevant git status so deletion/rename of a relevant
    # source file is detected even when the path no longer exists.
    for line in sorted(relevant_status):
        digest.update(b"STATUS\0")
        digest.update(
            line.encode(
                "utf-8",
                errors="surrogateescape",
            )
        )
        digest.update(b"\0")

    return {
        "path": str(repo),
        "available": True,
        "head": head,
        "full_repo_dirty": bool(status_lines),
        "full_repo_status_sha256": (
            hashlib.sha256(
                status.encode("utf-8")
            ).hexdigest()
        ),
        "full_modified_entry_count": len(
            status_lines
        ),
        "relevant_dirty": bool(
            relevant_status
        ),
        "relevant_modified_entry_count": len(
            relevant_status
        ),
        "relevant_file_count": len(files),
        "relevant_source_fingerprint_sha256": (
            digest.hexdigest()
        ),
        "relevant_globs": patterns,
        "excluded_prefixes": excluded_prefixes,
    }


def capture_sut_source_fingerprints() -> dict[str, Any]:
    return {
        "core": _relevant_source_fingerprint(
            Path(
                "/srv/green-server/"
                "seexr-api-core"
            ),
            patterns=CORE_RELEVANT_GLOBS,
        ),
        "agents": _relevant_source_fingerprint(
            Path(
                "/srv/green-server/"
                "seexr-api-agents"
            ),
            patterns=AGENTS_RELEVANT_GLOBS,
            excluded_prefixes=(
                AGENTS_EXCLUDED_PREFIXES
            ),
        ),
    }


def sut_source_matches(
    first: dict[str, Any],
    second: dict[str, Any],
) -> bool:
    for component in ("core", "agents"):
        left = first.get(component)
        right = second.get(component)
        if not isinstance(left, dict):
            return False
        if not isinstance(right, dict):
            return False
        if not left.get("available"):
            return False
        if not right.get("available"):
            return False
        if (
            left.get(
                "relevant_source_fingerprint_sha256"
            )
            != right.get(
                "relevant_source_fingerprint_sha256"
            )
        ):
            return False
    return True


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



def _judge_identity(judge: JudgeConfig) -> dict[str, Any]:
    return {
        "model": judge.model,
        "reasoning_effort": judge.reasoning_effort,
        "max_pairs_per_call": judge.max_pairs_per_call,
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
        "manifest_version": "1.1",
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
        "sut_source": (
            capture_sut_source_fingerprints()
        ),
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
            "dataset",
            "evaluation_artifacts",
            "source_tree_sha256",
            "method_identity",
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
        if not sut_source_matches(
            existing.get("sut_source", {}),
            manifest.get("sut_source", {}),
        ):
            mismatched.append("sut_source")
        if mismatched:
            raise RuntimeError(
                "Existing manifest does not "
                "match current run configuration: "
                f"{mismatched}"
            )
