from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import sha256_file
from .io_utils import atomic_write_json, load_json


SEAL_FILENAME = "run_seal.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _include_artifact(
    run_dir: Path,
    path: Path,
) -> bool:
    if not path.is_file():
        return False
    relative = path.relative_to(run_dir)
    if str(relative) == SEAL_FILENAME:
        return False
    if path.name.endswith(".tmp"):
        return False
    if path.name.startswith("."):
        return False
    return True


def _collect_artifacts(
    run_dir: Path,
) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(
        run_dir.rglob("*"),
        key=lambda value: str(
            value.relative_to(run_dir)
        ),
    ):
        if not _include_artifact(
            run_dir,
            path,
        ):
            continue
        artifacts.append(
            {
                "path": str(
                    path.relative_to(run_dir)
                ).replace("\\", "/"),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return artifacts


def _root_digest(
    artifacts: list[dict[str, Any]],
) -> str:
    digest = hashlib.sha256()
    for artifact in sorted(
        artifacts,
        key=lambda row: str(row["path"]),
    ):
        digest.update(
            str(artifact["path"]).encode(
                "utf-8"
            )
        )
        digest.update(b"\0")
        digest.update(
            str(artifact["sha256"]).encode(
                "ascii"
            )
        )
        digest.update(b"\0")
        digest.update(
            str(artifact["size"]).encode(
                "ascii"
            )
        )
        digest.update(b"\n")
    return digest.hexdigest()


def seal_run(
    run_dir: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest_path = (
        run_dir / "manifest.json"
    )
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Run manifest not found: {manifest_path}"
        )

    existing_seal = (
        run_dir / SEAL_FILENAME
    )
    previous_seal_sha256 = (
        sha256_file(existing_seal)
        if existing_seal.exists()
        else None
    )

    manifest = load_json(manifest_path)
    artifacts = _collect_artifacts(
        run_dir
    )
    payload = {
        "seal_version": "1.0",
        "created_at_utc": _utc_now(),
        "run_id": manifest.get("run_id"),
        "mode": manifest.get("mode"),
        "evaluation_git_head": (
            (manifest.get("git") or {}).get(
                "head"
            )
        ),
        "artifact_count": len(artifacts),
        "artifact_root_sha256": (
            _root_digest(artifacts)
        ),
        "previous_seal_sha256": (
            previous_seal_sha256
        ),
        "artifacts": artifacts,
    }
    atomic_write_json(
        existing_seal,
        payload,
    )
    return payload


def verify_run(
    run_dir: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    seal_path = run_dir / SEAL_FILENAME
    if not seal_path.exists():
        return {
            "ok": False,
            "error": "run_seal.json not found",
            "missing": [],
            "mismatched": [],
            "unexpected": [],
        }

    seal = load_json(seal_path)
    stored_artifacts = seal.get(
        "artifacts"
    )
    if not isinstance(
        stored_artifacts,
        list,
    ):
        return {
            "ok": False,
            "error": (
                "invalid seal artifact list"
            ),
            "missing": [],
            "mismatched": [],
            "unexpected": [],
        }

    stored_root = _root_digest(
        stored_artifacts
    )
    seal_internal_root_valid = (
        stored_root
        == seal.get(
            "artifact_root_sha256"
        )
    )

    expected = {
        str(row["path"]): row
        for row in stored_artifacts
        if isinstance(row, dict)
        and "path" in row
    }
    current_artifacts = (
        _collect_artifacts(run_dir)
    )
    current = {
        str(row["path"]): row
        for row in current_artifacts
    }

    missing = sorted(
        set(expected) - set(current)
    )
    unexpected = sorted(
        set(current) - set(expected)
    )
    mismatched: list[
        dict[str, Any]
    ] = []
    for relative in sorted(
        set(expected) & set(current)
    ):
        expected_row = expected[relative]
        current_row = current[relative]
        if (
            expected_row.get("sha256")
            != current_row.get("sha256")
            or int(
                expected_row.get(
                    "size",
                    -1,
                )
            )
            != int(
                current_row.get(
                    "size",
                    -2,
                )
            )
        ):
            mismatched.append(
                {
                    "path": relative,
                    "expected_sha256": (
                        expected_row.get(
                            "sha256"
                        )
                    ),
                    "actual_sha256": (
                        current_row.get(
                            "sha256"
                        )
                    ),
                    "expected_size": (
                        expected_row.get(
                            "size"
                        )
                    ),
                    "actual_size": (
                        current_row.get(
                            "size"
                        )
                    ),
                }
            )

    current_root = _root_digest(
        current_artifacts
    )
    root_matches_current = (
        current_root
        == seal.get(
            "artifact_root_sha256"
        )
    )

    ok = (
        seal_internal_root_valid
        and root_matches_current
        and not missing
        and not unexpected
        and not mismatched
    )
    return {
        "ok": ok,
        "run_id": seal.get("run_id"),
        "seal_version": seal.get(
            "seal_version"
        ),
        "artifact_count": len(
            stored_artifacts
        ),
        "artifact_root_sha256": (
            seal.get(
                "artifact_root_sha256"
            )
        ),
        "current_root_sha256": (
            current_root
        ),
        "seal_internal_root_valid": (
            seal_internal_root_valid
        ),
        "root_matches_current": (
            root_matches_current
        ),
        "missing": missing,
        "mismatched": mismatched,
        "unexpected": unexpected,
    }
