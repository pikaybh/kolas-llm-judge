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
