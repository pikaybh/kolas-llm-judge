import asyncio

import pytest

from kolas_llm_judge.binary_judge import (
    BinaryChecklistJudge,
    BinaryJudgeConfig,
    MatchChecklistDecision,
)


def test_binary_match_rule_keeps_accident_as_independent_metric() -> None:
    assert MatchChecklistDecision(
        id="x",
        same_hazard_mechanism=True,
        context_compatible=True,
        accident_compatible=True,
    ).is_match is True
    assert MatchChecklistDecision(
        id="x",
        same_hazard_mechanism=True,
        context_compatible=True,
        accident_compatible=False,
    ).is_match is True
    assert MatchChecklistDecision(
        id="x",
        same_hazard_mechanism=True,
        context_compatible=False,
        accident_compatible=True,
    ).is_match is False


def test_binary_judge_config_is_frozen_boolean_pipeline() -> None:
    cfg = BinaryJudgeConfig()
    assert cfg.pipeline_version == "binary-checklist-v1"
    assert cfg.model == "gpt-5.6-sol"
    assert cfg.max_concurrency >= 1


def test_binary_judge_id_validation_rejects_missing_or_duplicates() -> None:
    rows = [
        MatchChecklistDecision(
            id="a",
            same_hazard_mechanism=True,
            context_compatible=True,
            accident_compatible=True,
        )
    ]
    with pytest.raises(ValueError, match="completeness"):
        BinaryChecklistJudge._validate_ids(["a", "b"], rows, "match")
