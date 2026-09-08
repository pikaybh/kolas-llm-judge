from __future__ import annotations

from .models import (
    CaseJudgeResult,
    CaseMetrics,
    EvaluationScenario,
    GeneratedRisk,
    MetricValue,
    RiskMatch,
)


def _metric(numerator: int, denominator: int) -> MetricValue:
    return MetricValue(
        numerator=numerator,
        denominator=denominator,
        rate=(numerator / denominator) if denominator else None,
    )


def calculate_case_metrics(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    judge: CaseJudgeResult,
    matches: list[RiskMatch],
) -> CaseMetrics:
    generated_eval = {
        item.generated_id: item
        for item in judge.generated_evaluations
    }
    generated_by_id = {
        item.generated_id: item for item in generated
    }
    legal_matches = [
        match
        for match in matches
        if generated_by_id[match.generated_id].legal_basis
    ]

    return CaseMetrics(
        reference_risk_coverage=_metric(
            len(matches),
            len(scenario.references),
        ),
        unsupported_risk_rate=_metric(
            sum(
                bool(
                    generated_eval[
                        item.generated_id
                    ].unsupported_claim
                )
                for item in generated
            ),
            len(generated),
        ),
        accident_type_correctness=_metric(
            sum(
                match.accident_type_correctness == 2
                for match in matches
            ),
            len(matches),
        ),
        mitigation_appropriateness=_metric(
            sum(
                match.mitigation_appropriateness == 2
                for match in matches
            ),
            len(matches),
        ),
        mitigation_specificity=_metric(
            sum(
                match.mitigation_specificity == 2
                for match in matches
            ),
            len(matches),
        ),
        legal_basis_presence=_metric(
            len(legal_matches),
            len(matches),
        ),
        legal_basis_relevance=_metric(
            sum(
                match.legal_basis_relevance == 2
                for match in legal_matches
            ),
            len(legal_matches),
        ),
        critical_safety_error_rate=_metric(
            sum(
                bool(
                    generated_eval[
                        item.generated_id
                    ].critical_safety_error
                )
                for item in generated
            ),
            len(generated),
        ),
    )
