import asyncio

import pytest

from kolas_llm_judge.parallel_runner import ParallelRunnerConfig
from kolas_llm_judge.official_live import (
    _evenly_spaced_subset,
    execute_official_live,
)


def test_official_live_subset_is_deterministic_and_spans_range() -> None:
    items = list(range(100))
    selected = _evenly_spaced_subset(items, 5)
    assert selected == [0, 25, 50, 74, 99]
    assert _evenly_spaced_subset(items, 5) == selected


def test_official_live_rejects_partial_official_run_before_any_io(tmp_path) -> None:
    with pytest.raises(ValueError, match="development-only"):
        asyncio.run(
            execute_official_live(
                project_root=tmp_path,
                scenarios_path=tmp_path / "missing.jsonl",
                case_limit=10,
                development_mode=False,
            )
        )


def test_official_live_rejects_skipped_qualification_in_official_mode(tmp_path) -> None:
    with pytest.raises(ValueError, match="development-only"):
        asyncio.run(
            execute_official_live(
                project_root=tmp_path,
                scenarios_path=tmp_path / "missing.jsonl",
                development_mode=False,
                skip_qualification=True,
            )
        )


def test_official_live_rejects_runtime_override_in_official_mode(tmp_path) -> None:
    with pytest.raises(ValueError, match="development-only"):
        asyncio.run(
            execute_official_live(
                project_root=tmp_path,
                scenarios_path=tmp_path / "missing.jsonl",
                development_mode=False,
                runner_config=ParallelRunnerConfig(case_concurrency=99),
            )
        )

def test_development_instruction_exception_is_narrow_and_official_stays_strict() -> None:
    from kolas_llm_judge.official_live import _development_instruction_only_failure

    instruction_failure = {
        "checks": [
            {"name": "dataset_manifest", "ok": True},
            {"name": "evaluation_saved_instruction_empty", "ok": False},
        ]
    }
    assert _development_instruction_only_failure(instruction_failure, True)
    assert not _development_instruction_only_failure(instruction_failure, False)
    assert not _development_instruction_only_failure(
        {"checks": instruction_failure["checks"] + [{"name": "seexr_live_auth", "ok": False}]},
        True,
    )
    assert not _development_instruction_only_failure(
        {"checks": [{"name": "evaluation_saved_instruction_empty", "ok": True}]},
        True,
    )
