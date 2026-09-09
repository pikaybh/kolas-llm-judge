from pathlib import Path

from kolas_llm_judge.automated_report import collect_automated_report
from kolas_llm_judge.io_utils import atomic_write_json


def _metric(n: int, d: int):
    return {"numerator": n, "denominator": d, "rate": n / d if d else None}


def _write_fixture(tmp_path: Path, *, failure_class: str) -> None:
    atomic_write_json(
        tmp_path / "manifest.json",
        {
            "run_id": "official-test",
            "mode": "official-live",
            "selected_case_count": 2,
            "qualification": {"gate_pass": True},
        },
    )
    atomic_write_json(
        tmp_path / "completion.json",
        {"sut_source_stable": True, "auth_recovery_count": 1},
    )
    root = tmp_path / "cases" / "case-ok"
    atomic_write_json(
        root / "sut.json",
        {
            "elapsed_ms": 1000,
            "create_run_attempts": 1,
            "stream_reconnects": 0,
        },
    )
    atomic_write_json(
        root / "result.json",
        {
            "case_id": "case-ok",
            "scenario_input": {"process": "전기", "subprocess": None},
            "reference_count": 1,
            "generated_count": 2,
            "sut": {"elapsed_ms": 1000},
            "deterministic": {
                "schema_valid_items": 2,
                "item_count": 2,
                "post_improvement_mode": "blank",
                "checks": [
                    {
                        "frequency_in_range": True,
                        "severity_in_range": True,
                        "score_math_correct": True,
                        "post_frequency_in_range": None,
                        "post_severity_in_range": None,
                        "post_score_math_correct": None,
                        "post_risk_nonincreasing": None,
                    },
                    {
                        "frequency_in_range": True,
                        "severity_in_range": True,
                        "score_math_correct": True,
                        "post_frequency_in_range": None,
                        "post_severity_in_range": None,
                        "post_score_math_correct": None,
                        "post_risk_nonincreasing": None,
                    },
                ],
            },
            "metrics": {
                "reference_risk_coverage": _metric(1, 1),
                "accident_classification_agreement": _metric(1, 1),
                "mitigation_appropriateness": _metric(1, 1),
                "mitigation_actionability": _metric(1, 1),
                "mitigation_specificity": _metric(1, 1),
                "legal_basis_presence": _metric(1, 1),
                "legal_basis_relevance": _metric(1, 1),
                "unsafe_advice_rate": _metric(0, 1),
                "critical_safety_error_rate": _metric(0, 2),
            },
        },
    )
    atomic_write_json(
        root / "binary_judge.json",
        {
            "evaluation": {
                "calls": [
                    {
                        "stage": "match",
                        "response_model": "fake",
                        "usage": {
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "total_tokens": 15,
                        },
                    }
                ]
            }
        },
    )
    atomic_write_json(
        tmp_path / "cases" / "case-fail" / "error.json",
        {
            "case_id": "case-fail",
            "stage": "parse" if failure_class == "sut_non_completion" else "binary_judge",
            "failure_class": failure_class,
            "failure_reason": "ask_user" if failure_class == "sut_non_completion" else "judge_or_evaluator_failure",
            "error_type": "ValueError",
            "error": "test failure",
        },
    )


def test_sut_non_completion_is_measured_without_invalidating_procedure(tmp_path: Path) -> None:
    _write_fixture(tmp_path, failure_class="sut_non_completion")
    report = collect_automated_report(tmp_path)
    assert report["processed_cases"] == 2
    assert report["completed_cases"] == 1
    assert report["sut_completion_rate"]["rate"] == 0.5
    assert report["failure_classes"] == {"sut_non_completion": 1}
    assert report["procedure_valid"] is True
    assert report["deterministic"]["schema_compliance"]["rate"] == 1.0
    assert report["deterministic"]["checks"]["post_score_math_correct"]["rate"] is None
    assert report["judge_usage"]["total_tokens"] == 15


def test_evaluator_failure_invalidates_procedure(tmp_path: Path) -> None:
    _write_fixture(tmp_path, failure_class="evaluator_failure")
    report = collect_automated_report(tmp_path)
    assert report["procedure_valid"] is False
    assert report["evaluator_or_infrastructure_failure_count"] == 1


def test_old_result_backfills_hazard_identification_from_binary_matrix(tmp_path: Path) -> None:
    _write_fixture(tmp_path, failure_class="sut_non_completion")
    result_path = tmp_path / "cases" / "case-ok" / "result.json"
    result = __import__("json").loads(result_path.read_text(encoding="utf-8"))
    result["metrics"].pop("hazard_identification_accuracy", None)
    atomic_write_json(result_path, result)

    judge_path = tmp_path / "cases" / "case-ok" / "binary_judge.json"
    judge = __import__("json").loads(judge_path.read_text(encoding="utf-8"))
    judge["evaluation"]["match_matrix"] = [
        {
            "reference_id": "r1",
            "generated_id": "g1",
            "same_hazard_mechanism": False,
            "context_compatible": False,
            "accident_compatible": True,
        }
    ]
    atomic_write_json(judge_path, judge)

    report = collect_automated_report(tmp_path)
    metric = report["metrics"]["hazard_identification_accuracy"]
    assert metric == {"numerator": 1, "denominator": 1, "rate": 1.0}
