from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

MANIFEST_VERSION = "submission-integrity-v1"
DEFAULT_OUTPUT = Path("data/submission/submission_integrity_manifest_v1.json")

# 13_INTEGRITY_MANIFEST.md is intentionally excluded to avoid a self-referential
# cycle: it reports the machine manifest file SHA and artifact root.
SUBMISSION_DOCS = [
    "docs/submission_package/README.md",
    "docs/submission_package/MASTER_PLAN.md",
    "docs/submission_package/DOCUMENT_REGISTER.md",
    "docs/submission_package/HWP_HANDOFF_SPEC.md",
    "docs/submission_package/00_PHASE0_EVIDENCE_INVENTORY.md",
    "docs/submission_package/00_PHASE0_AUDIT_LOG.md",
    "docs/submission_package/01_TEST_METHOD.md",
    "docs/submission_package/02_SYSTEM_UNDER_TEST.md",
    "docs/submission_package/03_INFERENCE_CONFIGURATION.md",
    "docs/submission_package/04_GT_SPECIFICATION.md",
    "docs/submission_package/05_GT_SOURCE_PROVENANCE.md",
    "docs/submission_package/08_EVALUATOR_SPECIFICATION.md",
    "docs/submission_package/09_EVALUATOR_QUALIFICATION.md",
    "docs/submission_package/10_REPRODUCIBILITY_GUIDE.md",
    "docs/submission_package/11_API_ACCESS_GUIDE.md",
    "docs/submission_package/12_VERSION_MANIFEST.md",
    "docs/submission_package/14_CHANGE_CONTROL.md",
    "docs/submission_package/LAB_METHOD_DECISION_REGISTER.md",
    "docs/submission_package/SUT_FREEZE_CANDIDATE.md",
    "docs/submission_package/CLEAN_ROOM_REHEARSAL_20261011.md",
    "docs/submission_package/templates/SECTION_TEMPLATE.md",
    "docs/submission_package/templates/GT_PROVENANCE_REGISTER_TEMPLATE.csv",
]

CANONICAL_DATA = [
    "data/raw/PROVENANCE.md",
    "data/raw/kolas_v7_73_test.csv.bz2",
    "data/cases/scenarios_v1.jsonl",
    "data/cases/dataset_manifest.json",
    "data/cases/GT_CHANGELOG.md",
    "data/cases/gt_lineage_index_v1.csv",
    "data/cases/gt_provenance_register_v1.csv",
    "data/cases/gt_provenance_audit_manifest_v1.json",
]

SUBMISSION_EVIDENCE = [
    "data/submission/evidence/ajqg_20261011/binding.json",
    "data/submission/evidence/ajqg_20261011/summary.json",
    "data/submission/evidence/ajqg_20261011/control_results.csv",
    "data/submission/evidence/sut_freeze_20261011/candidate.json",
    "data/submission/evidence/stateful_snapshot_20261011/content_fingerprints.json",
]

PACKAGE_METADATA = [
    "README.md",
    ".env.example",
    "pyproject.toml",
    "uv.lock",
    "docs/automated_kolas_protocol_v1.md",
    "docs/evaluation_spec.md",
    "docs/kolas_compliance_plan_v1.md",
    "docs/testing_lab_method_and_rubric_v1.md",
    "tools/gt_provenance.py",
    "tools/build_submission_manifest.py",
]

GLOBS = [
    "src/kolas_llm_judge/*.py",
    "configs/*.yaml",
    "prompts/*.md",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_paths(project_root: Path) -> list[Path]:
    relative_paths = {Path(value) for value in SUBMISSION_DOCS + CANONICAL_DATA + SUBMISSION_EVIDENCE + PACKAGE_METADATA}
    for pattern in GLOBS:
        for path in project_root.glob(pattern):
            if path.is_file():
                relative_paths.add(path.relative_to(project_root))
    relative_paths.discard(DEFAULT_OUTPUT)
    relative_paths.discard(Path("docs/submission_package/13_INTEGRITY_MANIFEST.md"))
    return sorted(relative_paths, key=lambda p: p.as_posix())


def collect_artifacts(project_root: Path, relative_paths: Iterable[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    missing: list[str] = []
    for relative in sorted(set(relative_paths), key=lambda p: p.as_posix()):
        path = project_root / relative
        if not path.is_file():
            missing.append(relative.as_posix())
            continue
        rows.append(
            {
                "path": relative.as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if missing:
        raise FileNotFoundError("Missing required submission artifact(s): " + ", ".join(missing))
    return rows


def artifact_root_sha256(artifacts: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(artifacts, key=lambda x: str(x["path"])):
        digest.update(str(row["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(row["sha256"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(row["size"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _git_head(project_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def build_manifest(
    project_root: Path,
    output_path: Path = DEFAULT_OUTPUT,
    relative_paths: Iterable[Path] | None = None,
) -> dict[str, object]:
    project_root = project_root.resolve()
    paths = list(relative_paths) if relative_paths is not None else candidate_paths(project_root)
    artifacts = collect_artifacts(project_root, paths)
    generator_relative = Path("tools/build_submission_manifest.py")
    generator_path = project_root / generator_relative
    payload: dict[str, object] = {
        "manifest_version": MANIFEST_VERSION,
        "status": "CANDIDATE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_base_head_at_generation": _git_head(project_root),
        "generator": {
            "path": generator_relative.as_posix(),
            "sha256": sha256_file(generator_path) if generator_path.is_file() else None,
        },
        "scope": {
            "includes_secret_values": False,
            "includes_run_directories": False,
            "includes_integrity_report_md": False,
            "integrity_report_exclusion_reason": "Avoid self-reference; the report records this manifest file SHA-256 and artifact root.",
        },
        "artifact_count": len(artifacts),
        "artifact_root_sha256": artifact_root_sha256(artifacts),
        "artifacts": artifacts,
    }
    absolute_output = output_path if output_path.is_absolute() else project_root / output_path
    absolute_output.parent.mkdir(parents=True, exist_ok=True)
    absolute_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def verify_manifest(project_root: Path, manifest_path: Path = DEFAULT_OUTPUT) -> dict[str, object]:
    project_root = project_root.resolve()
    absolute_manifest = manifest_path if manifest_path.is_absolute() else project_root / manifest_path
    payload = json.loads(absolute_manifest.read_text(encoding="utf-8"))
    stored = payload.get("artifacts")
    if not isinstance(stored, list):
        return {"ok": False, "error": "invalid artifacts list", "missing": [], "mismatched": []}

    missing: list[str] = []
    mismatched: list[dict[str, object]] = []
    current_rows: list[dict[str, object]] = []
    for row in stored:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            return {"ok": False, "error": "invalid artifact row", "missing": [], "mismatched": []}
        relative = Path(str(row["path"]))
        path = project_root / relative
        if not path.is_file():
            missing.append(relative.as_posix())
            continue
        actual = {
            "path": relative.as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        current_rows.append(actual)
        if actual["size"] != row.get("size") or actual["sha256"] != row.get("sha256"):
            mismatched.append(
                {
                    "path": relative.as_posix(),
                    "expected_size": row.get("size"),
                    "actual_size": actual["size"],
                    "expected_sha256": row.get("sha256"),
                    "actual_sha256": actual["sha256"],
                }
            )

    stored_root = artifact_root_sha256(stored)  # validates internal list/root consistency
    current_root = artifact_root_sha256(current_rows) if not missing else None
    expected_root = payload.get("artifact_root_sha256")
    internal_root_valid = stored_root == expected_root
    current_root_matches = current_root == expected_root if current_root is not None else False
    ok = not missing and not mismatched and internal_root_valid and current_root_matches
    return {
        "ok": ok,
        "manifest_path": str(absolute_manifest),
        "artifact_count": len(stored),
        "missing": missing,
        "mismatched": mismatched,
        "internal_root_valid": internal_root_valid,
        "current_root_matches": current_root_matches,
        "expected_root_sha256": expected_root,
        "current_root_sha256": current_root,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify KOLAS submission integrity manifest")
    parser.add_argument("action", choices=["build", "verify"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output)
    if args.action == "build":
        manifest = build_manifest(root, output)
        print(json.dumps({
            "artifact_count": manifest["artifact_count"],
            "artifact_root_sha256": manifest["artifact_root_sha256"],
            "output": str(output),
        }, ensure_ascii=False, indent=2))
        return 0

    result = verify_manifest(root, output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
