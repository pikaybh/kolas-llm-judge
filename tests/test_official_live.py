import asyncio

import pytest

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
