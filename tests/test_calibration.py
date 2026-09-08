from __future__ import annotations

import csv
from pathlib import Path

from kolas_llm_judge.calibration import (
    GENERATED_DIMENSIONS,
    MATCH_DIMENSIONS,
    QUALITY_DIMENSIONS,
    make_human_calibration_template,
    score_human_calibration,
)
from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.models import (
    CaseJudgeResult,
    EvaluationScenario,
    GeneratedJudgeResult,
    GeneratedRisk,
    PairJudgeResult,
    ReferenceRisk,
    ScenarioInput,
)


def _build_calibration_fixture(
    tmp_path: Path,
) -> tuple[Path, Path]:
    run_dir = tmp_path / "run"
    case_dir = run_dir / "cases/case-cal"
    case_dir.mkdir(parents=True)

    scenario = EvaluationScenario(
        case_id="case-cal",
        source_rows=[2],
        input=ScenarioInput(
            process="전기",
            subprocess="배선",
            equipment=["분전반"],
            materials=["전선"],
        ),
        references=[
            ReferenceRisk(
                reference_id="case-cal-r2",
                source_row=2,
                hazard="활선 접촉 감전",
                accident_types=["감전"],
                mitigation="전원 차단 후 작업",
                legal_basis="산업안전보건기준에 관한 규칙",
            )
        ],
    )
    scenarios_path = tmp_path / "scenarios.jsonl"
    scenarios_path.write_text(
        scenario.model_dump_json() + "\n",
        encoding="utf-8",
    )

    risk = GeneratedRisk(
        generated_id="g001",
        hazard="활선 접촉으로 감전될 위험",
        accident_types=["감전"],
        mitigation="전원 차단 후 무전압 확인",
        legal_basis="산업안전보건기준에 관한 규칙",
    )
    judge = CaseJudgeResult(
        pair_evaluations=[
            PairJudgeResult(
                reference_id="case-cal-r2",
                generated_id="g001",
                semantic_match=4,
                accident_type_correctness=2,
                mitigation_appropriateness=2,
                mitigation_specificity=2,
                legal_basis_relevance=2,
                explanation="동일 위험과 적합한 통제",
            )
        ],
        generated_evaluations=[
            GeneratedJudgeResult(
                generated_id="g001",
                unsupported_claim=False,
                critical_safety_error=False,
                explanation="작업 맥락에 근거함",
            )
        ],
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
        case_dir / "judge.json",
        {
            "result": judge.model_dump(
                mode="json"
            )
        },
    )
    atomic_write_json(
        case_dir / "result.json",
        {
            "status": "completed",
            "case_id": "case-cal",
            "reference_count": 1,
            "matches": [
                {
                    "reference_id": "case-cal-r2",
                    "generated_id": "g001",
                }
            ],
        },
    )
    atomic_write_json(
        run_dir / "manifest.json",
        {
            "run_id": "pilot-test",
            "git": {
                "head": "pilot-commit",
                "dirty": False,
            },
            "sut_evaluation_identity": {
                "base_url": "https://api.seexr.dev/api",
                "agent_id": "risk-assessment",
                "risk_assessment_method": "빈도강도법 5x4",
                "model_mode": "fast",
                "reasoning_style": "balanced",
                "post_improvement_mode": "blank",
            },
            "method_identity": {
                "dataset_sha256": "dataset-test",
                "evaluation_artifacts": {
                    "prompts/judge_v1.md": "prompt-test",
                    "configs/rubric_v1.yaml": "rubric-test",
                },
                "source_tree_sha256": "source-test",
                "judge": {
                    "model": "judge-test",
                    "reasoning_effort": "medium",
                    "max_pairs_per_call": 120,
                    "prompt_path": "prompts/judge_v1.md",
                    "rubric_path": "configs/rubric_v1.yaml",
                },
            },
        },
    )
    return run_dir, scenarios_path


def _fill_pair_labels(
    path: Path,
    *,
    override: dict[str, str] | None = None,
) -> None:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    defaults = {
        "semantic_match": "4",
        "accident_type_correctness": "2",
    }
    if override:
        defaults.update(override)

    for dimension, value in defaults.items():
        rows[0][f"rater1_{dimension}"] = value
        rows[0][f"rater2_{dimension}"] = value
        rows[0][f"adjudicated_{dimension}"] = value

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)



def _fill_quality_labels(
    path: Path,
    *,
    override: dict[str, str] | None = None,
) -> None:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    defaults = {
        "mitigation_appropriateness": "2",
        "mitigation_specificity": "2",
        "legal_basis_relevance": "2",
    }
    if override:
        defaults.update(override)

    for dimension, value in defaults.items():
        rows[0][f"rater1_{dimension}"] = value
        rows[0][f"rater2_{dimension}"] = value
        rows[0][f"adjudicated_{dimension}"] = value

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)

def _fill_generated_labels(
    path: Path,
    *,
    override: dict[str, str] | None = None,
) -> None:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    defaults = {
        "unsupported_claim": "0",
        "critical_safety_error": "0",
    }
    if override:
        defaults.update(override)

    for dimension, value in defaults.items():
        rows[0][f"rater1_{dimension}"] = value
        rows[0][f"rater2_{dimension}"] = value
        rows[0][f"adjudicated_{dimension}"] = value

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def _repeatability_file(
    run_dir: Path,
) -> Path:
    path = (
        run_dir
        / "calibration/repeatability/summary.json"
    )
    atomic_write_json(
        path,
        {
            "repeatability": 1.0,
            "minimum_dimension_repeatability": 1.0,
        },
    )
    return path


def test_multidimensional_calibration_template_hides_judge(
    tmp_path: Path,
) -> None:
    run_dir, scenarios_path = (
        _build_calibration_fixture(tmp_path)
    )
    paths = make_human_calibration_template(
        run_dir=run_dir,
        scenarios_path=scenarios_path,
        output_dir=run_dir / "calibration",
        sample_size=1,
        generated_sample_size=1,
    )

    pair_text = paths["pairs"].read_text(
        encoding="utf-8-sig"
    )
    quality_text = paths[
        "quality_pairs"
    ].read_text(encoding="utf-8-sig")
    generated_text = paths[
        "generated"
    ].read_text(encoding="utf-8-sig")
    assert "_judge_" not in pair_text
    assert "judge_score" not in pair_text
    assert "_judge_" not in quality_text
    assert "judge_score" not in quality_text
    assert "_judge_" not in generated_text
    assert "judge_score" not in generated_text

    for dimension in MATCH_DIMENSIONS:
        assert f"rater1_{dimension}" in pair_text
    for dimension in QUALITY_DIMENSIONS:
        assert f"rater1_{dimension}" in quality_text
    for dimension in GENERATED_DIMENSIONS:
        assert (
            f"rater1_{dimension}"
            in generated_text
        )

    _fill_pair_labels(paths["pairs"])
    _fill_quality_labels(paths["quality_pairs"])
    _fill_generated_labels(
        paths["generated"]
    )
    result = score_human_calibration(
        run_dir=run_dir,
        labeled_pairs_csv=paths["pairs"],
        labeled_quality_pairs_csv=paths["quality_pairs"],
        labeled_generated_csv=paths["generated"],
        repeatability_summary=(
            _repeatability_file(run_dir)
        ),
        min_pair_samples=1,
        min_quality_samples=1,
        min_generated_samples=1,
    )

    assert (
        result["match_dimensions"][
            "semantic_match"
        ]["judge_human_binary_agreement"]
        == 1.0
    )
    assert (
        result["generated_dimensions"][
            "critical_safety_error"
        ]["judge_human_agreement"]
        == 1.0
    )
    assert result["structured_completion"]["matched_quality"]["rate"] == 1.0
    assert result["gate_pass"] is True


def test_calibration_gate_fails_when_one_dimension_disagrees(
    tmp_path: Path,
) -> None:
    run_dir, scenarios_path = (
        _build_calibration_fixture(tmp_path)
    )
    paths = make_human_calibration_template(
        run_dir=run_dir,
        scenarios_path=scenarios_path,
        output_dir=run_dir / "calibration",
        sample_size=1,
        generated_sample_size=1,
    )

    _fill_pair_labels(paths["pairs"])
    _fill_quality_labels(
        paths["quality_pairs"],
        override={"mitigation_appropriateness": "0"},
    )
    _fill_generated_labels(
        paths["generated"]
    )
    result = score_human_calibration(
        run_dir=run_dir,
        labeled_pairs_csv=paths["pairs"],
        labeled_quality_pairs_csv=paths["quality_pairs"],
        labeled_generated_csv=paths["generated"],
        repeatability_summary=(
            _repeatability_file(run_dir)
        ),
        min_pair_samples=1,
        min_quality_samples=1,
        min_generated_samples=1,
    )

    check = result["checks"][
        "mitigation_appropriateness_agreement"
    ]
    assert check["value"] == 0.0
    assert check["pass"] is False
    assert result["gate_pass"] is False


def test_calibration_gate_requires_complete_human_labels(
    tmp_path: Path,
) -> None:
    run_dir, scenarios_path = (
        _build_calibration_fixture(tmp_path)
    )
    paths = make_human_calibration_template(
        run_dir=run_dir,
        scenarios_path=scenarios_path,
        output_dir=run_dir / "calibration",
        sample_size=1,
        generated_sample_size=1,
    )

    _fill_pair_labels(paths["pairs"])
    _fill_quality_labels(paths["quality_pairs"])
    _fill_generated_labels(
        paths["generated"]
    )

    with paths["quality_pairs"].open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())
    rows[0][
        "rater1_mitigation_specificity"
    ] = ""
    rows[0][
        "rater2_mitigation_specificity"
    ] = ""
    rows[0][
        "adjudicated_mitigation_specificity"
    ] = ""
    with paths["quality_pairs"].open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)

    result = score_human_calibration(
        run_dir=run_dir,
        labeled_pairs_csv=paths["pairs"],
        labeled_quality_pairs_csv=paths["quality_pairs"],
        labeled_generated_csv=paths["generated"],
        repeatability_summary=(
            _repeatability_file(run_dir)
        ),
        min_pair_samples=0,
        min_quality_samples=0,
        min_generated_samples=1,
    )
    assert (
        result["checks"][
            "human_label_completion"
        ]["pass"]
        is False
    )
    assert result["gate_pass"] is False


def test_repeatability_tracks_match_assignment_changes() -> None:
    from collections import defaultdict
    from kolas_llm_judge.calibration import _append_repeatability_decisions

    scenario = EvaluationScenario(
        case_id="case-repeat",
        source_rows=[2],
        input=ScenarioInput(process="전기"),
        references=[
            ReferenceRisk(
                reference_id="r1",
                source_row=2,
                hazard="감전",
            )
        ],
    )
    generated = [
        GeneratedRisk(generated_id="g1", hazard="감전 A"),
        GeneratedRisk(generated_id="g2", hazard="감전 B"),
    ]

    def make_result(g1_score: int, g2_score: int) -> CaseJudgeResult:
        return CaseJudgeResult(
            pair_evaluations=[
                PairJudgeResult(
                    reference_id="r1",
                    generated_id="g1",
                    semantic_match=g1_score,
                    accident_type_correctness=2,
                    quality_evaluated=(g1_score > g2_score),
                    explanation="",
                ),
                PairJudgeResult(
                    reference_id="r1",
                    generated_id="g2",
                    semantic_match=g2_score,
                    accident_type_correctness=2,
                    quality_evaluated=(g2_score > g1_score),
                    explanation="",
                ),
            ],
            generated_evaluations=[
                GeneratedJudgeResult(
                    generated_id="g1",
                    unsupported_claim=False,
                    critical_safety_error=False,
                    explanation="",
                ),
                GeneratedJudgeResult(
                    generated_id="g2",
                    unsupported_claim=False,
                    critical_safety_error=False,
                    explanation="",
                ),
            ],
        )

    decisions = {
        dimension: defaultdict(list)
        for dimension in (
            *MATCH_DIMENSIONS.keys(),
            *QUALITY_DIMENSIONS.keys(),
            *GENERATED_DIMENSIONS,
            "match_assignment",
        )
    }
    _append_repeatability_decisions(
        scenario=scenario,
        generated=generated,
        result=make_result(4, 3),
        decisions=decisions,
    )
    _append_repeatability_decisions(
        scenario=scenario,
        generated=generated,
        result=make_result(3, 4),
        decisions=decisions,
    )
    assert decisions["match_assignment"]["case-repeat:r1"] == ["g1", "g2"]
