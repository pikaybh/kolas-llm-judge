from pathlib import Path

import pytest

from kolas_llm_judge.qualification_controls import (
    load_generated_control_suite,
    validate_control_suite,
)


def test_ajqg_control_suite_is_complete_deterministic_and_hashed() -> None:
    first = load_generated_control_suite()
    second = load_generated_control_suite()
    validate_control_suite(first)
    assert len(first.controls) == 8 * 13
    assert first.controls_sha256 == second.controls_sha256
    assert [x.control_id for x in first.controls] == [
        x.control_id for x in second.controls
    ]
    assert first.counts_by_family == {
        "match_identity": 8,
        "match_negative": 8,
        "accident": 16,
        "mitigation": 32,
        "legal": 16,
        "critical_safety": 16,
        "robustness": 8,
    }


def test_ajqg_expected_answers_are_construction_defined() -> None:
    suite = load_generated_control_suite()
    by_id = {x.control_id: x for x in suite.controls}
    assert by_id["fall:match-identity"].expected == {
        "same_hazard_mechanism": True,
        "context_compatible": True,
        "accident_compatible": True,
    }
    assert by_id["fall:match-negative"].expected == {
        "same_hazard_mechanism": False,
        "context_compatible": False,
        "accident_compatible": False,
    }
    assert by_id["electric:mitigation-unsafe"].expected["unsafe_advice"] is True
    assert by_id["fire:legal-negative"].expected["legal_basis_relevant"] is False
    assert by_id["collapse:critical-unsafe"].expected["critical_safety_error"] is True


def test_ajqg_seed_file_exists() -> None:
    assert Path("configs/ajqg_seed_v1.yaml").exists()
    assert Path("configs/ajqg_gate_v1.yaml").exists()
