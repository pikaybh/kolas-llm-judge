from __future__ import annotations

from kolas_llm_judge.manifest import (
    capture_sut_api_contract,
    method_identity_matches,
    sut_api_contract_matches,
)
from kolas_llm_judge.sut_client import SutConfig


def test_observable_api_contract_is_stable_without_server_files() -> None:
    config = SutConfig(base_url="https://api.seexr.co.kr/api")
    payload = {"agents": [{"id": "risk-assessment", "enabled": True}]}
    first = capture_sut_api_contract(payload, config)
    second = capture_sut_api_contract(payload, config)
    assert first["available"] is True
    assert sut_api_contract_matches(first, second) is True
    assert "path" not in first and "head" not in first


def test_api_contract_fails_closed_on_change_or_missing_agent() -> None:
    config = SutConfig(base_url="https://api.seexr.co.kr/api")
    first = capture_sut_api_contract({"agents": [{"id": "risk-assessment"}]}, config)
    changed = capture_sut_api_contract(
        {"agents": [{"id": "risk-assessment"}, {"id": "other"}]}, config
    )
    missing = capture_sut_api_contract({"agents": []}, config)
    assert sut_api_contract_matches(first, changed) is False
    assert sut_api_contract_matches(first, missing) is False


def test_method_identity_requires_exact_frozen_match() -> None:
    frozen = {
        "dataset_sha256": "dataset",
        "source_tree_sha256": "source",
        "evaluation_artifacts": {
            "prompts/judge_v1.md": "prompt",
        },
        "judge": {
            "model": "judge-model",
        },
    }
    same = dict(frozen)
    changed = {
        **frozen,
        "judge": {
            "model": "different-model",
        },
    }
    assert method_identity_matches(
        frozen,
        same,
    ) is True
    assert method_identity_matches(
        frozen,
        changed,
    ) is False
