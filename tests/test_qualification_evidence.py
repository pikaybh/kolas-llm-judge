from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.dataset import sha256_file
from kolas_llm_judge.qualification_evidence import (validate_qualification_evidence, capture_frozen_qualification_identity, FROZEN_FILES)

FILES = FROZEN_FILES


def fixture(root: Path, *, passed=True, minutes_ago=1) -> Path:
    for relative in FILES.values():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative)
    folder = root / "runs" / "_qualification" / "test-qual"
    folder.mkdir(parents=True)
    (folder / "control_results.csv").write_text("control_id,correct\nitem-1,true\n")
    atomic_write_json(folder / "summary.json", {
        "gate_pass": passed, "qualification_version": "ajqg-v1",
        "control_count": 104, "repeats": 2,
        "completed_at_utc": (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(),
        "judge": {"model":"gpt-5.6-sol", "reasoning_effort":"medium"},
        "frozen_evaluator": capture_frozen_qualification_identity(root),
    })
    return folder


def test_fresh_pass_is_linked_and_once_only(tmp_path):
    p=fixture(tmp_path)
    proof, path=validate_qualification_evidence(tmp_path,expected_model="gpt-5.6-sol",expected_effort="medium")
    assert path == p/"summary.json"
    assert proof["gate_pass"] is True
    manifest=tmp_path/"runs"/"official-1"/"manifest.json"
    atomic_write_json(manifest, {"qualification":proof})
    with pytest.raises(RuntimeError,match="AJQG_REQUIRED"):
        validate_qualification_evidence(tmp_path,expected_model="gpt-5.6-sol",expected_effort="medium")


@pytest.mark.parametrize("passed,age", [(False,1),(True,180)])
def test_fail_and_stale_proofs_block_official(tmp_path,passed,age):
    fixture(tmp_path,passed=passed,minutes_ago=age)
    with pytest.raises(RuntimeError,match="AJQG_REQUIRED"):
        validate_qualification_evidence(tmp_path,expected_model="gpt-5.6-sol",expected_effort="medium")


def test_prompt_change_invalidates_qualification(tmp_path):
    fixture(tmp_path)
    (tmp_path/"prompts/judge_binary_v1.md").write_text("modified")
    with pytest.raises(RuntimeError,match="AJQG_REQUIRED"):
        validate_qualification_evidence(tmp_path,expected_model="gpt-5.6-sol",expected_effort="medium")


def test_qualification_identity_tracks_runtime_and_evaluator_source(tmp_path):
    folder = fixture(tmp_path)
    from kolas_llm_judge.io_utils import load_json
    captured = load_json(folder / "summary.json")["frozen_evaluator"]
    assert captured["runtime_sha256"] == sha256_file(tmp_path / "configs/official_runtime_v2.yaml")
    assert captured["evaluator_source_sha256"] == capture_frozen_qualification_identity(tmp_path)["evaluator_source_sha256"]
    (tmp_path / "configs/official_runtime_v2.yaml").write_text("modified runtime")
    with pytest.raises(RuntimeError,match="AJQG_REQUIRED"):
        validate_qualification_evidence(tmp_path, expected_model="gpt-5.6-sol", expected_effort="medium")
