from __future__ import annotations

from kolas_llm_judge.manifest import (
    method_identity_matches,
    sut_source_matches,
)


def _sut_component(
    fingerprint: str,
    *,
    full_status: str,
) -> dict[str, object]:
    return {
        "available": True,
        "relevant_source_fingerprint_sha256": fingerprint,
        "full_repo_status_sha256": full_status,
        "full_repo_dirty": True,
    }


def test_sut_stability_ignores_unrelated_repo_status_changes() -> None:
    first = {
        "core": _sut_component(
            "core-same",
            full_status="full-a",
        ),
        "agents": _sut_component(
            "agents-same",
            full_status="full-a",
        ),
    }
    second = {
        "core": _sut_component(
            "core-same",
            full_status="full-b",
        ),
        "agents": _sut_component(
            "agents-same",
            full_status="full-c",
        ),
    }
    assert sut_source_matches(first, second) is True


def test_sut_stability_detects_relevant_source_change() -> None:
    first = {
        "core": _sut_component(
            "core-a",
            full_status="same",
        ),
        "agents": _sut_component(
            "agents-a",
            full_status="same",
        ),
    }
    second = {
        "core": _sut_component(
            "core-b",
            full_status="same",
        ),
        "agents": _sut_component(
            "agents-a",
            full_status="same",
        ),
    }
    assert sut_source_matches(first, second) is False


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
