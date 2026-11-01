from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.dataset import sha256_file
from kolas_llm_judge.qualification_evidence import validate_qualification_evidence

FILES = {
    "prompt_sha256": "prompts/judge_binary_v1.md",
    "rubric_sha256": "configs/rubric_binary_v1.yaml",
    "gate_sha256": "configs/ajqg_gate_v1.yaml",
    "seed_sha256": "configs/ajqg_seed_v1.yaml",
}


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
        "frozen_evaluator": {k:sha256_file(root/v) for k,v in FILES.items()},
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
