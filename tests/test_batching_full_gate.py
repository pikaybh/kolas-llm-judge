from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from kolas_llm_judge.judge import iter_pair_batches
from kolas_llm_judge.models import (
    EvaluationScenario,
    GeneratedRisk,
    ReferenceRisk,
    ScenarioInput,
)
from kolas_llm_judge.runner import execute_run


def test_pair_batching_is_complete_and_unique() -> None:
    scenario = EvaluationScenario(
        case_id="case-batch",
        source_rows=[2, 3],
        input=ScenarioInput(process="공정"),
        references=[
            ReferenceRisk(
                reference_id="r1",
                source_row=2,
                hazard="위험1",
            ),
            ReferenceRisk(
                reference_id="r2",
                source_row=3,
                hazard="위험2",
            ),
        ],
    )
    generated = [
        GeneratedRisk(generated_id=f"g{i}", hazard=f"생성{i}")
        for i in range(1, 4)
    ]
    batches = iter_pair_batches(
        scenario,
        generated,
        batch_size=4,
    )
    assert [len(batch) for batch in batches] == [4, 2]
    pairs = [
        (reference.reference_id, risk.generated_id)
        for batch in batches
        for reference, risk in batch
    ]
    assert len(pairs) == 6
    assert len(set(pairs)) == 6
    assert set(pairs) == {
        ("r1", "g1"),
        ("r1", "g2"),
        ("r1", "g3"),
        ("r2", "g1"),
        ("r2", "g2"),
        ("r2", "g3"),
    }


def test_full_run_requires_calibration_gate(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        RuntimeError,
        match="requires a passed calibration gate",
    ):
        asyncio.run(
            execute_run(
                project_root=tmp_path,
                scenarios_path=tmp_path / "missing.jsonl",
                mode="full",
            )
        )


def test_full_run_blocks_calibration_method_mismatch(
    tmp_path: Path,
) -> None:
    scenario = EvaluationScenario(
        case_id="case-full",
        source_rows=[2],
        input=ScenarioInput(process="공정"),
        references=[
            ReferenceRisk(
                reference_id="case-full-r2",
                source_row=2,
                hazard="위험",
            )
        ],
    )
    scenarios_path = tmp_path / "scenarios.jsonl"
    scenarios_path.write_text(
        scenario.model_dump_json() + "\n",
        encoding="utf-8",
    )
    gate_path = tmp_path / "gate_result.json"
    gate_path.write_text(
        '''{
  "gate_pass": true,
  "frozen_method": {
    "source_run_id": "pilot-test",
    "method_identity": {
      "dataset_sha256": "definitely-wrong",
      "evaluation_artifacts": {},
      "source_tree_sha256": "wrong",
      "judge": {}
    }
  }
}\n''',
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="differs from the calibrated frozen method",
    ):
        asyncio.run(
            execute_run(
                project_root=tmp_path,
                scenarios_path=scenarios_path,
                mode="full",
                calibration_gate_path=gate_path,
            )
        )


def test_full_run_blocks_calibration_sut_setting_mismatch(
    tmp_path: Path,
) -> None:
    import json

    from kolas_llm_judge.judge import JudgeConfig
    from kolas_llm_judge.manifest import (
        capture_current_method_identity,
        sut_evaluation_identity,
    )
    from kolas_llm_judge.sut_client import SutConfig

    scenario = EvaluationScenario(
        case_id="case-full-sut",
        source_rows=[2],
        input=ScenarioInput(process="공정"),
        references=[
            ReferenceRisk(
                reference_id="case-full-sut-r2",
                source_row=2,
                hazard="위험",
            )
        ],
    )
    scenarios_path = tmp_path / "scenarios.jsonl"
    scenarios_path.write_text(
        scenario.model_dump_json() + "\n",
        encoding="utf-8",
    )
    judge = JudgeConfig.from_env()
    current_method = capture_current_method_identity(
        project_root=tmp_path,
        scenarios_path=scenarios_path,
        judge=judge,
    )
    mismatched_sut = sut_evaluation_identity(
        SutConfig(model_mode="pro")
    )
    gate_path = tmp_path / "gate_result.json"
    gate_path.write_text(
        json.dumps(
            {
                "gate_pass": True,
                "frozen_method": {
                    "source_run_id": "pilot-test",
                    "method_identity": current_method,
                    "sut_evaluation_identity": mismatched_sut,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="SUT evaluation settings differ",
    ):
        asyncio.run(
            execute_run(
                project_root=tmp_path,
                scenarios_path=scenarios_path,
                mode="full",
                calibration_gate_path=gate_path,
            )
        )


def _selection_scenario(process: str, index: int) -> EvaluationScenario:
    return EvaluationScenario(
        case_id=f"case-{process}-{index}",
        source_rows=[index + 2],
        input=ScenarioInput(process=process, subprocess=f"세부-{index}"),
        references=[
            ReferenceRisk(
                reference_id=f"r-{process}-{index}",
                source_row=index + 2,
                hazard=f"위험-{process}-{index}",
            )
        ],
    )


def test_pilot_selection_prioritizes_process_diversity() -> None:
    from kolas_llm_judge.runner import select_cases

    scenarios: list[EvaluationScenario] = []
    for process_index in range(80):
        process = f"공정-{process_index:03d}"
        for scenario_index in range(3):
            scenarios.append(
                _selection_scenario(
                    process,
                    process_index * 10 + scenario_index,
                )
            )

    selected = select_cases(
        scenarios,
        mode="pilot",
        pilot_cases=50,
    )
    assert len(selected) == 50
    assert len({case.input.process for case in selected}) == 50
    assert [case.case_id for case in selected] == [
        case.case_id
        for case in select_cases(
            scenarios,
            mode="pilot",
            pilot_cases=50,
        )
    ]


def test_pilot_selection_uses_median_scenario_within_process() -> None:
    from kolas_llm_judge.runner import select_cases

    scenarios = [
        _selection_scenario("A", 0),
        _selection_scenario("A", 1),
        _selection_scenario("A", 2),
        _selection_scenario("B", 3),
        _selection_scenario("B", 4),
        _selection_scenario("B", 5),
    ]
    selected = select_cases(
        scenarios,
        mode="pilot",
        pilot_cases=2,
    )
    assert [case.input.process for case in selected] == ["A", "B"]
    assert [case.input.subprocess for case in selected] == ["세부-1", "세부-4"]


def test_pilot_selection_fills_after_all_processes_are_covered() -> None:
    from kolas_llm_judge.runner import select_cases

    scenarios = [
        _selection_scenario("A", 0),
        _selection_scenario("A", 1),
        _selection_scenario("B", 2),
        _selection_scenario("B", 3),
        _selection_scenario("C", 4),
        _selection_scenario("C", 5),
    ]
    selected = select_cases(
        scenarios,
        mode="pilot",
        pilot_cases=5,
    )
    assert len(selected) == 5
    assert len({case.case_id for case in selected}) == 5
    assert {case.input.process for case in selected} == {"A", "B", "C"}


def test_selection_metadata_records_pilot_strategy() -> None:
    from kolas_llm_judge.runner import _selection_metadata, select_cases

    scenarios = [
        _selection_scenario(f"P{i:02d}", i)
        for i in range(60)
    ]
    selected = select_cases(
        scenarios,
        mode="pilot",
        pilot_cases=50,
    )
    metadata = _selection_metadata(
        scenarios,
        selected,
        mode="pilot",
    )
    assert metadata["strategy"] == "process-diverse-evenly-spaced-median-v1"
    assert metadata["available_process_count"] == 60
    assert metadata["selected_process_count"] == 50
    assert metadata["selected_case_count"] == 50
    assert len(metadata["selected_processes"]) == 50
