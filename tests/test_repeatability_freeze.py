from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from kolas_llm_judge.calibration import (
    run_judge_repeatability,
)
from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.models import (
    EvaluationScenario,
    GeneratedRisk,
    ReferenceRisk,
    ScenarioInput,
)


def test_repeatability_blocks_method_identity_mismatch(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "runs/pilot-test"
    case_dir = run_dir / "cases/case-r"
    case_dir.mkdir(parents=True)

    scenario = EvaluationScenario(
        case_id="case-r",
        source_rows=[2],
        input=ScenarioInput(process="공정"),
        references=[
            ReferenceRisk(
                reference_id="case-r-r2",
                source_row=2,
                hazard="위험",
            )
        ],
    )
    scenarios_path = (
        tmp_path / "data/cases/scenarios.jsonl"
    )
    scenarios_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    scenarios_path.write_text(
        scenario.model_dump_json() + "\n",
        encoding="utf-8",
    )

    risk = GeneratedRisk(
        generated_id="g001",
        hazard="생성 위험",
    )
    atomic_write_json(
        case_dir / "parsed.json",
        {
            "parsed": {
                "method": "빈도강도법 5x4",
                "risks": [
                    risk.model_dump(mode="json")
                ],
                "xml": "<risk_assessment/>",
                "equipment": [],
                "materials": [],
                "trailing_text": "",
            },
            "deterministic": {
                "xml_parse_success": True,
                "item_count": 1,
                "schema_valid_items": 1,
                "checks": [],
                "errors": [],
            },
        },
    )
    atomic_write_json(
        run_dir / "manifest.json",
        {
            "run_id": "pilot-test",
            "method_identity": {
                "dataset_sha256": "wrong",
                "evaluation_artifacts": {},
                "source_tree_sha256": "wrong",
                "judge": {},
            },
        },
    )

    with pytest.raises(
        RuntimeError,
        match="differs from the pilot run",
    ):
        asyncio.run(
            run_judge_repeatability(
                run_dir=run_dir,
                scenarios_path=scenarios_path,
                output_dir=(
                    run_dir
                    / "calibration/repeatability"
                ),
                project_root=tmp_path,
                repeats=2,
                max_cases=1,
            )
        )
