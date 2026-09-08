import pytest

from kolas_llm_judge.judge import validate_judge_completeness
from kolas_llm_judge.models import (
    CaseJudgeResult, EvaluationScenario, GeneratedJudgeResult, GeneratedRisk,
    PairJudgeResult, ReferenceRisk, ScenarioInput,
)


def test_judge_matrix_must_be_complete() -> None:
    scenario = EvaluationScenario(case_id="c", source_rows=[2], input=ScenarioInput(process="p"), references=[ReferenceRisk(reference_id="r", source_row=2, hazard="h")])
    generated = [GeneratedRisk(generated_id="g", hazard="x")]
    incomplete = CaseJudgeResult(pair_evaluations=[], generated_evaluations=[GeneratedJudgeResult(generated_id="g", unsupported_claim=False, critical_safety_error=False, explanation="")])
    with pytest.raises(ValueError):
        validate_judge_completeness(scenario, generated, incomplete)

    complete = CaseJudgeResult(
        pair_evaluations=[PairJudgeResult(reference_id="r", generated_id="g", semantic_match=3, accident_type_correctness=2, mitigation_appropriateness=2, mitigation_specificity=2, legal_basis_relevance=1, explanation="ok")],
        generated_evaluations=[GeneratedJudgeResult(generated_id="g", unsupported_claim=False, critical_safety_error=False, explanation="ok")],
    )
    validate_judge_completeness(scenario, generated, complete)
