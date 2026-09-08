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


def test_pair_batch_input_deduplicates_payload_objects() -> None:
    import json
    from kolas_llm_judge.judge import build_pair_batch_input

    scenario = EvaluationScenario(
        case_id="batch",
        source_rows=[2, 3],
        input=ScenarioInput(process="철근공사"),
        references=[
            ReferenceRisk(reference_id="r1", source_row=2, hazard="고유위험문구A"),
            ReferenceRisk(reference_id="r2", source_row=3, hazard="고유위험문구B"),
        ],
    )
    generated = [
        GeneratedRisk(generated_id="g1", hazard="고유생성문구1"),
        GeneratedRisk(generated_id="g2", hazard="고유생성문구2"),
        GeneratedRisk(generated_id="g3", hazard="고유생성문구3"),
    ]
    pairs = [
        (reference, risk)
        for reference in scenario.references
        for risk in generated
    ]
    raw = build_pair_batch_input(scenario, pairs)
    payload = json.loads(raw)

    assert len(payload["references"]) == 2
    assert len(payload["generated_risks"]) == 3
    assert len(payload["pairs"]) == 6
    assert all(
        set(pair) == {"reference_id", "generated_id"}
        for pair in payload["pairs"]
    )
    assert raw.count("고유위험문구A") == 1
    assert raw.count("고유위험문구B") == 1
    assert raw.count("고유생성문구1") == 1
    assert raw.count("고유생성문구2") == 1
    assert raw.count("고유생성문구3") == 1
