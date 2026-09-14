from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import numpy as np
from pydantic import BaseModel
from scipy.optimize import linear_sum_assignment

from .binary_judge import (
    BinaryChecklistJudge,
    MatchChecklistDecision,
    QualityChecklistDecision,
    SafetyChecklistDecision,
)
from .identification import (
    hazard_identification_metric,
    hazard_semantic_identification_metric,
)
from .models import (
    EvaluationScenario,
    GeneratedRisk,
    MetricValue,
    ReferenceRisk,
)


class BinaryMatchRecord(BaseModel):
    reference_id: str
    generated_id: str
    same_hazard_mechanism: bool
    context_compatible: bool
    accident_compatible: bool


class BinaryQualityRecord(BaseModel):
    reference_id: str
    generated_id: str
    mitigation_addresses_hazard: bool
    mitigation_actionable: bool
    mitigation_specific: bool
    unsafe_advice: bool
    legal_basis_relevant: bool


class BinarySafetyRecord(BaseModel):
    generated_id: str
    critical_safety_error: bool


class AutomatedCaseMetrics(BaseModel):
    # KOLAS-primary semantic identification: same hazard mechanism + compatible context.
    # This is reference-level and many-to-one; accident compatibility alone is insufficient.
    hazard_semantic_identification_recall: MetricValue

    # Supplementary KPI-compatible, reference-level identification metric.
    # A reference is identified when at least one generated risk either
    # (a) matches the same hazard mechanism in a compatible context, or
    # (b) captures a safety-engineering-compatible accident/damage mechanism.
    # This is intentionally many-to-one and is kept separate from the stricter
    # 1:1 Reference Risk Coverage diagnostic.
    hazard_identification_accuracy: MetricValue
    reference_risk_coverage: MetricValue
    accident_classification_agreement: MetricValue
    mitigation_appropriateness: MetricValue
    mitigation_actionability: MetricValue
    mitigation_specificity: MetricValue
    legal_basis_presence: MetricValue
    legal_basis_relevance: MetricValue
    unsafe_advice_rate: MetricValue
    critical_safety_error_rate: MetricValue


class BinaryCaseEvaluation(BaseModel):
    match_matrix: list[BinaryMatchRecord]
    matches: list[BinaryMatchRecord]
    quality: list[BinaryQualityRecord]
    safety: list[BinarySafetyRecord]
    metrics: AutomatedCaseMetrics
    calls: list[dict[str, Any]]


@dataclass(frozen=True)
class BinaryEvaluationConfig:
    match_chunk_size: int = 80
    quality_chunk_size: int = 40
    safety_chunk_size: int = 50


def _metric(numerator: int, denominator: int) -> MetricValue:
    return MetricValue(
        numerator=numerator,
        denominator=denominator,
        rate=(numerator / denominator) if denominator else None,
    )


def _chunks[T](items: list[T], size: int) -> list[list[T]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]


def _call_metadata(call: Any) -> dict[str, Any]:
    return {
        "stage": call.stage,
        "response_id": call.response_id,
        "response_model": call.response_model,
        "usage": call.usage,
        "elapsed_ms": call.elapsed_ms,
        "row_count": len(call.rows),
    }


def _pair_id(reference_id: str, generated_id: str) -> str:
    return f"{reference_id}::{generated_id}"


def _maximum_binary_matches(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    matrix: list[BinaryMatchRecord],
) -> list[BinaryMatchRecord]:
    if not scenario.references or not generated:
        return []
    by_key = {
        (row.reference_id, row.generated_id): row
        for row in matrix
    }
    n_ref = len(scenario.references)
    n_gen = len(generated)
    weights = np.zeros((n_ref, n_gen), dtype=np.int64)

    # Count of covered references dominates all secondary preferences.
    # Accident compatibility is independent of match eligibility but is used
    # as a secondary preference among equally coverable assignments.
    cardinality_weight = 10**12
    accident_weight = 10**8
    for i, reference in enumerate(scenario.references):
        for j, risk in enumerate(generated):
            row = by_key.get((reference.reference_id, risk.generated_id))
            if row is None:
                raise ValueError(
                    "Missing binary match decision: "
                    f"{reference.reference_id}/{risk.generated_id}"
                )
            if not (
                row.same_hazard_mechanism
                and row.context_compatible
            ):
                continue
            stable_tie = (n_ref - i) * (n_gen + 1) + (n_gen - j)
            weights[i, j] = (
                cardinality_weight
                + (accident_weight if row.accident_compatible else 0)
                + stable_tie
            )

    rows, cols = linear_sum_assignment(weights, maximize=True)
    selected: list[BinaryMatchRecord] = []
    for i, j in zip(rows.tolist(), cols.tolist()):
        if weights[i, j] <= 0:
            continue
        reference = scenario.references[i]
        risk = generated[j]
        selected.append(by_key[(reference.reference_id, risk.generated_id)])
    return selected


async def _evaluate_match_matrix(
    judge: BinaryChecklistJudge,
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    *,
    chunk_size: int,
) -> tuple[list[BinaryMatchRecord], list[dict[str, Any]]]:
    pairs = [
        (reference, risk)
        for reference in scenario.references
        for risk in generated
    ]
    if not pairs:
        return [], []
    calls = await asyncio.gather(
        *[
            judge.evaluate_match_pairs(scenario, chunk)
            for chunk in _chunks(pairs, chunk_size)
        ]
    )
    decisions: dict[str, MatchChecklistDecision] = {}
    metadata: list[dict[str, Any]] = []
    for call in calls:
        metadata.append(_call_metadata(call))
        for row in call.rows:
            decision = MatchChecklistDecision.model_validate(row)
            if decision.id in decisions:
                raise ValueError(f"Duplicate binary match decision: {decision.id}")
            decisions[decision.id] = decision

    result: list[BinaryMatchRecord] = []
    for reference, risk in pairs:
        key = _pair_id(reference.reference_id, risk.generated_id)
        decision = decisions.get(key)
        if decision is None:
            raise ValueError(f"Missing binary match decision: {key}")
        result.append(
            BinaryMatchRecord(
                reference_id=reference.reference_id,
                generated_id=risk.generated_id,
                same_hazard_mechanism=decision.same_hazard_mechanism,
                context_compatible=decision.context_compatible,
                accident_compatible=decision.accident_compatible,
            )
        )
    return result, metadata


async def _evaluate_quality(
    judge: BinaryChecklistJudge,
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    matches: list[BinaryMatchRecord],
    *,
    chunk_size: int,
) -> tuple[list[BinaryQualityRecord], list[dict[str, Any]]]:
    if not matches:
        return [], []
    refs = {x.reference_id: x for x in scenario.references}
    gens = {x.generated_id: x for x in generated}
    pairs: list[tuple[ReferenceRisk, GeneratedRisk]] = [
        (refs[x.reference_id], gens[x.generated_id])
        for x in matches
    ]
    calls = await asyncio.gather(
        *[
            judge.evaluate_quality_pairs(scenario, chunk)
            for chunk in _chunks(pairs, chunk_size)
        ]
    )
    decisions: dict[str, QualityChecklistDecision] = {}
    metadata: list[dict[str, Any]] = []
    for call in calls:
        metadata.append(_call_metadata(call))
        for row in call.rows:
            decision = QualityChecklistDecision.model_validate(row)
            if decision.id in decisions:
                raise ValueError(f"Duplicate binary quality decision: {decision.id}")
            decisions[decision.id] = decision

    result: list[BinaryQualityRecord] = []
    for reference, risk in pairs:
        key = _pair_id(reference.reference_id, risk.generated_id)
        decision = decisions.get(key)
        if decision is None:
            raise ValueError(f"Missing binary quality decision: {key}")
        result.append(
            BinaryQualityRecord(
                reference_id=reference.reference_id,
                generated_id=risk.generated_id,
                mitigation_addresses_hazard=decision.mitigation_addresses_hazard,
                mitigation_actionable=decision.mitigation_actionable,
                mitigation_specific=decision.mitigation_specific,
                unsafe_advice=decision.unsafe_advice,
                legal_basis_relevant=decision.legal_basis_relevant,
            )
        )
    return result, metadata


async def _evaluate_safety(
    judge: BinaryChecklistJudge,
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    *,
    chunk_size: int,
) -> tuple[list[BinarySafetyRecord], list[dict[str, Any]]]:
    if not generated:
        return [], []
    calls = await asyncio.gather(
        *[
            judge.evaluate_safety_risks(scenario, chunk)
            for chunk in _chunks(generated, chunk_size)
        ]
    )
    decisions: dict[str, SafetyChecklistDecision] = {}
    metadata: list[dict[str, Any]] = []
    for call in calls:
        metadata.append(_call_metadata(call))
        for row in call.rows:
            decision = SafetyChecklistDecision.model_validate(row)
            if decision.id in decisions:
                raise ValueError(f"Duplicate binary safety decision: {decision.id}")
            decisions[decision.id] = decision
    result: list[BinarySafetyRecord] = []
    for risk in generated:
        decision = decisions.get(risk.generated_id)
        if decision is None:
            raise ValueError(f"Missing binary safety decision: {risk.generated_id}")
        result.append(
            BinarySafetyRecord(
                generated_id=risk.generated_id,
                critical_safety_error=decision.critical_safety_error,
            )
        )
    return result, metadata


def _calculate_metrics(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    match_matrix: list[BinaryMatchRecord],
    matches: list[BinaryMatchRecord],
    quality: list[BinaryQualityRecord],
    safety: list[BinarySafetyRecord],
) -> AutomatedCaseMetrics:
    quality_by_key = {
        (x.reference_id, x.generated_id): x
        for x in quality
    }
    generated_by_id = {x.generated_id: x for x in generated}
    safety_by_id = {x.generated_id: x for x in safety}

    matched_quality = [
        quality_by_key[(x.reference_id, x.generated_id)]
        for x in matches
    ]
    legal_matches = [
        x
        for x in matches
        if bool(generated_by_id[x.generated_id].legal_basis)
    ]
    legal_quality = [
        quality_by_key[(x.reference_id, x.generated_id)]
        for x in legal_matches
    ]

    reference_ids = [reference.reference_id for reference in scenario.references]
    semantic_identification = hazard_semantic_identification_metric(
        match_matrix,
        reference_ids,
    )
    identification = hazard_identification_metric(
        match_matrix,
        reference_ids,
    )

    return AutomatedCaseMetrics(
        hazard_semantic_identification_recall=semantic_identification,
        hazard_identification_accuracy=identification,
        reference_risk_coverage=_metric(len(matches), len(scenario.references)),
        accident_classification_agreement=_metric(
            sum(x.accident_compatible for x in matches),
            len(matches),
        ),
        mitigation_appropriateness=_metric(
            sum(x.mitigation_addresses_hazard for x in matched_quality),
            len(matched_quality),
        ),
        mitigation_actionability=_metric(
            sum(x.mitigation_actionable for x in matched_quality),
            len(matched_quality),
        ),
        mitigation_specificity=_metric(
            sum(x.mitigation_specific for x in matched_quality),
            len(matched_quality),
        ),
        legal_basis_presence=_metric(len(legal_matches), len(matches)),
        legal_basis_relevance=_metric(
            sum(x.legal_basis_relevant for x in legal_quality),
            len(legal_quality),
        ),
        unsafe_advice_rate=_metric(
            sum(x.unsafe_advice for x in matched_quality),
            len(matched_quality),
        ),
        critical_safety_error_rate=_metric(
            sum(
                safety_by_id[risk.generated_id].critical_safety_error
                for risk in generated
            ),
            len(generated),
        ),
    )


async def evaluate_binary_case(
    *,
    judge: BinaryChecklistJudge,
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    config: BinaryEvaluationConfig | None = None,
) -> BinaryCaseEvaluation:
    config = config or BinaryEvaluationConfig()
    match_matrix, match_calls = await _evaluate_match_matrix(
        judge,
        scenario,
        generated,
        chunk_size=config.match_chunk_size,
    )
    matches = _maximum_binary_matches(scenario, generated, match_matrix)

    quality_task = _evaluate_quality(
        judge,
        scenario,
        generated,
        matches,
        chunk_size=config.quality_chunk_size,
    )
    safety_task = _evaluate_safety(
        judge,
        scenario,
        generated,
        chunk_size=config.safety_chunk_size,
    )
    (quality, quality_calls), (safety, safety_calls) = await asyncio.gather(
        quality_task,
        safety_task,
    )
    metrics = _calculate_metrics(
        scenario,
        generated,
        match_matrix,
        matches,
        quality,
        safety,
    )
    return BinaryCaseEvaluation(
        match_matrix=match_matrix,
        matches=matches,
        quality=quality,
        safety=safety,
        metrics=metrics,
        calls=[*match_calls, *quality_calls, *safety_calls],
    )
