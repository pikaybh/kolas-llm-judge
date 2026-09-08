from kolas_llm_judge.matching import match_risks
from kolas_llm_judge.metrics import calculate_case_metrics
from kolas_llm_judge.models import (
    CaseJudgeResult, EvaluationScenario, GeneratedJudgeResult, GeneratedRisk,
    PairJudgeResult, ReferenceRisk, ScenarioInput,
)


def _pair(r: str, g: str, semantic: int, accident: int = 2, mitigation: int = 2, legal: int = 2):
    return PairJudgeResult(
        reference_id=r, generated_id=g, semantic_match=semantic,
        accident_type_correctness=accident, mitigation_appropriateness=mitigation,
        mitigation_specificity=mitigation, legal_basis_relevance=legal,
        explanation="test",
    )


def test_hungarian_matching_and_metrics() -> None:
    scenario = EvaluationScenario(
        case_id="c1", source_rows=[2, 3], input=ScenarioInput(process="공정"),
        references=[
            ReferenceRisk(reference_id="r1", source_row=2, hazard="추락"),
            ReferenceRisk(reference_id="r2", source_row=3, hazard="감전"),
        ],
    )
    generated = [
        GeneratedRisk(generated_id="g1", hazard="감전 위험"),
        GeneratedRisk(generated_id="g2", hazard="추락 위험"),
        GeneratedRisk(generated_id="g3", hazard="근거 없는 위험"),
    ]
    judge = CaseJudgeResult(
        pair_evaluations=[
            _pair("r1", "g1", 0), _pair("r1", "g2", 4), _pair("r1", "g3", 0),
            _pair("r2", "g1", 4), _pair("r2", "g2", 0), _pair("r2", "g3", 0),
        ],
        generated_evaluations=[
            GeneratedJudgeResult(generated_id="g1", unsupported_claim=False, critical_safety_error=False, explanation=""),
            GeneratedJudgeResult(generated_id="g2", unsupported_claim=False, critical_safety_error=False, explanation=""),
            GeneratedJudgeResult(generated_id="g3", unsupported_claim=True, critical_safety_error=False, explanation=""),
        ],
    )
    matches = match_risks(scenario, generated, judge)
    assert {(m.reference_id, m.generated_id) for m in matches} == {("r1", "g2"), ("r2", "g1")}
    metrics = calculate_case_metrics(scenario, generated, judge, matches)
    assert metrics.reference_risk_coverage.rate == 1.0
    assert metrics.unsupported_risk_rate.numerator == 1
    assert metrics.unsupported_risk_rate.denominator == 3
