import asyncio

from kolas_llm_judge.binary_evaluation import (
    BinaryEvaluationConfig,
    evaluate_binary_case,
)
from kolas_llm_judge.binary_judge import (
    BinaryJudgeCall,
    MatchChecklistDecision,
    QualityChecklistDecision,
    SafetyChecklistDecision,
)
from kolas_llm_judge.models import (
    EvaluationScenario,
    GeneratedRisk,
    ReferenceRisk,
    ScenarioInput,
)


class FakeBinaryJudge:
    def __init__(self) -> None:
        self.match_calls = 0
        self.quality_calls = 0
        self.safety_calls = 0

    async def evaluate_match_pairs(self, scenario, pairs):
        self.match_calls += 1
        rows = []
        for reference, risk in pairs:
            good = reference.reference_id[-1] == risk.generated_id[-1]
            accident = not (
                reference.reference_id == "r2"
                and risk.generated_id == "g2"
            )
            rows.append(
                MatchChecklistDecision(
                    id=f"{reference.reference_id}::{risk.generated_id}",
                    same_hazard_mechanism=good,
                    context_compatible=good,
                    accident_compatible=accident if good else False,
                )
            )
        return BinaryJudgeCall("match", rows, "m", "fake", {}, 1)

    async def evaluate_quality_pairs(self, scenario, pairs):
        self.quality_calls += 1
        rows = [
            QualityChecklistDecision(
                id=f"{reference.reference_id}::{risk.generated_id}",
                mitigation_addresses_hazard=True,
                mitigation_actionable=True,
                mitigation_specific=(reference.reference_id != "r2"),
                unsafe_advice=False,
                legal_basis_relevant=True,
            )
            for reference, risk in pairs
        ]
        return BinaryJudgeCall("quality", rows, "q", "fake", {}, 1)

    async def evaluate_safety_risks(self, scenario, generated):
        self.safety_calls += 1
        rows = [
            SafetyChecklistDecision(
                id=risk.generated_id,
                critical_safety_error=(risk.generated_id == "g3"),
            )
            for risk in generated
        ]
        return BinaryJudgeCall("safety", rows, "s", "fake", {}, 1)


def scenario_fixture() -> tuple[EvaluationScenario, list[GeneratedRisk]]:
    scenario = EvaluationScenario(
        case_id="binary-case",
        source_rows=[2, 3],
        input=ScenarioInput(process="테스트 공정"),
        references=[
            ReferenceRisk(
                reference_id="r1",
                source_row=2,
                hazard="감전",
                accident_types=["감전"],
                mitigation="전원차단",
                legal_basis="법규A",
            ),
            ReferenceRisk(
                reference_id="r2",
                source_row=3,
                hazard="추락",
                accident_types=["추락"],
                mitigation="안전난간",
                legal_basis="법규B",
            ),
        ],
    )
    generated = [
        GeneratedRisk(
            generated_id="g1",
            hazard="감전",
            mitigation="전원차단",
            legal_basis="법규A",
        ),
        GeneratedRisk(
            generated_id="g2",
            hazard="추락",
            mitigation="안전난간",
            legal_basis="법규B",
        ),
        GeneratedRisk(
            generated_id="g3",
            hazard="화재",
            mitigation="소화기",
            legal_basis=None,
        ),
    ]
    return scenario, generated


def test_binary_case_evaluation_keeps_accident_metric_independent() -> None:
    scenario, generated = scenario_fixture()
    judge = FakeBinaryJudge()
    result = asyncio.run(
        evaluate_binary_case(
            judge=judge,
            scenario=scenario,
            generated=generated,
            config=BinaryEvaluationConfig(
                match_chunk_size=2,
                quality_chunk_size=1,
                safety_chunk_size=2,
            ),
        )
    )
    assert len(result.match_matrix) == 6
    assert len(result.matches) == 2
    assert result.metrics.reference_risk_coverage.rate == 1.0
    assert result.metrics.accident_classification_agreement.rate == 0.5
    assert result.metrics.mitigation_appropriateness.rate == 1.0
    assert result.metrics.mitigation_specificity.rate == 0.5
    assert result.metrics.legal_basis_presence.rate == 1.0
    assert result.metrics.critical_safety_error_rate.numerator == 1
    assert result.metrics.critical_safety_error_rate.denominator == 3
    assert judge.match_calls == 3
    assert judge.quality_calls == 2
    assert judge.safety_calls == 2


def test_binary_case_with_no_match_has_nullable_matched_metrics() -> None:
    scenario, generated = scenario_fixture()

    class NoMatchJudge(FakeBinaryJudge):
        async def evaluate_match_pairs(self, scenario, pairs):
            return BinaryJudgeCall(
                "match",
                [
                    MatchChecklistDecision(
                        id=f"{r.reference_id}::{g.generated_id}",
                        same_hazard_mechanism=False,
                        context_compatible=False,
                        accident_compatible=False,
                    )
                    for r, g in pairs
                ],
                "m",
                "fake",
                {},
                1,
            )

    result = asyncio.run(
        evaluate_binary_case(
            judge=NoMatchJudge(),
            scenario=scenario,
            generated=generated,
        )
    )
    assert result.metrics.reference_risk_coverage.rate == 0.0
    assert result.metrics.accident_classification_agreement.rate is None
    assert result.metrics.mitigation_appropriateness.rate is None
    assert result.metrics.legal_basis_presence.rate is None


def test_hazard_identification_accuracy_is_broader_than_strict_1to1_coverage() -> None:
    scenario, generated = scenario_fixture()

    class AccidentOnlyJudge(FakeBinaryJudge):
        async def evaluate_match_pairs(self, scenario, pairs):
            rows = []
            for reference, risk in pairs:
                accident = (
                    reference.reference_id == "r1"
                    and risk.generated_id == "g3"
                )
                rows.append(
                    MatchChecklistDecision(
                        id=f"{reference.reference_id}::{risk.generated_id}",
                        same_hazard_mechanism=False,
                        context_compatible=False,
                        accident_compatible=accident,
                    )
                )
            return BinaryJudgeCall("match", rows, "m", "fake", {}, 1)

    result = asyncio.run(
        evaluate_binary_case(
            judge=AccidentOnlyJudge(),
            scenario=scenario,
            generated=generated,
        )
    )
    assert result.metrics.reference_risk_coverage.rate == 0.0
    assert result.metrics.hazard_identification_accuracy.numerator == 1
    assert result.metrics.hazard_identification_accuracy.denominator == 2
    assert result.metrics.hazard_identification_accuracy.rate == 0.5
