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


def test_match_stage_payload_excludes_quality_fields() -> None:
    import json
    from kolas_llm_judge.judge import build_pair_batch_input

    scenario = EvaluationScenario(
        case_id="no-quality-leak",
        source_rows=[2],
        input=ScenarioInput(process="전기"),
        references=[
            ReferenceRisk(
                reference_id="r1",
                source_row=2,
                hazard="감전 위험",
                accident_types=["감전"],
                mitigation="기준대책-절대포함금지",
                legal_basis="기준법규-절대포함금지",
            )
        ],
    )
    risk = GeneratedRisk(
        generated_id="g1",
        hazard="활선 접촉 감전",
        accident_types=["감전"],
        mitigation="생성대책-절대포함금지",
        legal_basis="생성법규-절대포함금지",
    )
    raw = build_pair_batch_input(
        scenario,
        [(scenario.references[0], risk)],
    )
    payload = json.loads(raw)
    assert "기준대책-절대포함금지" not in raw
    assert "기준법규-절대포함금지" not in raw
    assert "생성대책-절대포함금지" not in raw
    assert "생성법규-절대포함금지" not in raw
    assert set(payload["references"][0]) == {
        "reference_id", "hazard", "accident_types"
    }
    assert set(payload["generated_risks"][0]) == {
        "generated_id", "hazard", "risk_cause", "accident_types"
    }


def test_two_stage_judge_evaluates_quality_only_for_selected_match() -> None:
    import asyncio
    from kolas_llm_judge.judge import JudgeConfig, LlmJudge
    from kolas_llm_judge.models import (
        PairMatchJudgeResult,
        PairQualityJudgeResult,
    )

    scenario = EvaluationScenario(
        case_id="two-stage",
        source_rows=[2],
        input=ScenarioInput(process="전기"),
        references=[
            ReferenceRisk(
                reference_id="r1",
                source_row=2,
                hazard="활선 접촉 감전",
                accident_types=["감전"],
                mitigation="전원 차단",
                legal_basis="법규",
            )
        ],
    )
    generated = [
        GeneratedRisk(
            generated_id="g1",
            hazard="활선 접촉으로 감전",
            accident_types=["감전"],
            mitigation="LOTO",
            legal_basis="법규",
        ),
        GeneratedRisk(
            generated_id="g2",
            hazard="자재에 걸려 넘어짐",
            accident_types=["넘어짐"],
            mitigation="정리정돈",
        ),
    ]

    class FakeJudge(LlmJudge):
        def __init__(self) -> None:
            self.config = JudgeConfig(
                max_pairs_per_call=80,
                max_concurrency=3,
            )
            self.quality_inputs: list[list[tuple[str, str]]] = []

        async def _match_batch(self, scenario, batch, batch_index):
            rows = []
            for reference, risk in batch:
                if risk.generated_id == "g1":
                    rows.append(
                        PairMatchJudgeResult(r=reference.reference_id, g=risk.generated_id, s=4, a=2)
                    )
                else:
                    rows.append(
                        PairMatchJudgeResult(r=reference.reference_id, g=risk.generated_id, s=1, a=0)
                    )
            return rows, {
                "stage": "match",
                "batch_index": batch_index,
                "response_id": f"m{batch_index}",
                "response_model": "fake",
                "usage": {"total_tokens": 1},
            }

        async def _generated_safety(self, scenario, generated):
            return [
                GeneratedJudgeResult(
                    generated_id=risk.generated_id,
                    unsupported_claim=False,
                    critical_safety_error=False,
                    explanation="",
                )
                for risk in generated
            ], {
                "stage": "safety",
                "batch_index": None,
                "response_id": "s1",
                "response_model": "fake",
                "usage": {"total_tokens": 1},
            }

        async def _quality_batch(self, scenario, generated, matched_ids):
            self.quality_inputs.append(list(matched_ids))
            return [
                PairQualityJudgeResult(
                    r=reference_id,
                    g=generated_id,
                    m=2,
                    p=2,
                    l=2,
                    e="적합",
                )
                for reference_id, generated_id in matched_ids
            ], {
                "stage": "quality",
                "batch_index": None,
                "response_id": "q1",
                "response_model": "fake",
                "usage": {"total_tokens": 1},
            }

    judge = FakeJudge()
    record = asyncio.run(judge.evaluate_case(scenario, generated))
    pair_map = {
        (p.reference_id, p.generated_id): p
        for p in record.result.pair_evaluations
    }
    assert judge.quality_inputs == [[("r1", "g1")]]
    assert pair_map[("r1", "g1")].quality_evaluated is True
    assert pair_map[("r1", "g1")].mitigation_appropriateness == 2
    assert pair_map[("r1", "g2")].quality_evaluated is False
    assert pair_map[("r1", "g2")].mitigation_appropriateness == 0
    assert [call["stage"] for call in record.calls] == [
        "match", "safety", "quality"
    ]
