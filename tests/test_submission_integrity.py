from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_submission_manifest import (
    DEFAULT_OUTPUT,
    artifact_root_sha256,
    build_manifest,
    candidate_paths,
    sha256_file,
    verify_manifest,
)


def test_candidate_scope_has_no_self_reference_or_secrets() -> None:
    paths = candidate_paths(ROOT)
    values = {p.as_posix() for p in paths}
    assert DEFAULT_OUTPUT.as_posix() not in values
    assert "docs/submission_package/13_INTEGRITY_MANIFEST.md" not in values
    assert ".env" not in values
    assert ".env.example" in values
    assert "data/raw/kolas_v7_73_test.csv.bz2" in values
    assert "data/cases/scenarios_v1.jsonl" in values
    assert "tools/build_submission_manifest.py" in values
    assert "data/submission/evidence/ajqg_20261011/binding.json" in values
    assert "data/submission/evidence/ajqg_20261011/summary.json" in values
    assert "data/submission/evidence/ajqg_20261011/control_results.csv" in values


def test_candidate_paths_all_exist() -> None:
    paths = candidate_paths(ROOT)
    assert paths
    assert all((ROOT / path).is_file() for path in paths)


def test_manifest_build_and_verify_detects_tamper(tmp_path: Path) -> None:
    project = tmp_path / "p"
    project.mkdir()
    (project / "a.txt").write_text("alpha\n", encoding="utf-8")
    (project / "b.txt").write_text("beta\n", encoding="utf-8")
    output = project / "manifest.json"
    payload = build_manifest(
        project,
        output,
        relative_paths=[Path("a.txt"), Path("b.txt")],
    )
    assert payload["artifact_count"] == 2
    assert payload["artifact_root_sha256"] == artifact_root_sha256(payload["artifacts"])
    assert verify_manifest(project, output)["ok"] is True

    (project / "b.txt").write_text("tampered\n", encoding="utf-8")
    result = verify_manifest(project, output)
    assert result["ok"] is False
    assert result["mismatched"][0]["path"] == "b.txt"


def test_real_candidate_manifest_matches_files_when_present() -> None:
    path = ROOT / DEFAULT_OUTPUT
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["artifact_root_sha256"] == artifact_root_sha256(payload["artifacts"])
    assert verify_manifest(ROOT, path)["ok"] is True
    assert sha256_file(ROOT / "data/raw/kolas_v7_73_test.csv.bz2") == (
        "b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a"
    )
