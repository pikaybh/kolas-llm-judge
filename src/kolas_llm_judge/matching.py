from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from .models import (
    CaseJudgeResult,
    EvaluationScenario,
    GeneratedRisk,
    RiskMatch,
)


def select_match_ids(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    judge: CaseJudgeResult,
    *,
    threshold: int = 3,
) -> list[tuple[str, str]]:
    """Select 1:1 matches using hazard semantics only.

    Mitigation/legal quality is deliberately excluded from matching so
    downstream quality metrics cannot influence which pair is selected.
    Accident type is used only as a deterministic secondary tie-breaker.
    """
    if not scenario.references or not generated:
        return []

    pair_map = {
        (pair.reference_id, pair.generated_id): pair
        for pair in judge.pair_evaluations
    }
    weights = np.zeros(
        (
            len(scenario.references),
            len(generated),
        ),
        dtype=np.int64,
    )
    for i, reference in enumerate(
        scenario.references
    ):
        for j, risk in enumerate(generated):
            pair = pair_map.get(
                (
                    reference.reference_id,
                    risk.generated_id,
                )
            )
            if pair is None:
                raise ValueError(
                    "Missing pair score: "
                    f"{reference.reference_id}/"
                    f"{risk.generated_id}"
                )
            if (
                pair.semantic_match
                >= threshold
            ):
                # Semantic score dominates accident
                # tie-breaking. Stable input order
                # resolves exact ties.
                weights[i, j] = (
                    pair.semantic_match * 100
                    + pair.accident_type_correctness
                )

    rows, cols = linear_sum_assignment(
        weights,
        maximize=True,
    )
    selected: list[tuple[str, str]] = []
    for row, col in zip(
        rows.tolist(),
        cols.tolist(),
    ):
        if weights[row, col] <= 0:
            continue
        reference = scenario.references[row]
        risk = generated[col]
        pair = pair_map[
            (
                reference.reference_id,
                risk.generated_id,
            )
        ]
        if pair.semantic_match < threshold:
            continue
        selected.append(
            (
                reference.reference_id,
                risk.generated_id,
            )
        )
    return selected


def match_risks(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    judge: CaseJudgeResult,
    *,
    threshold: int = 3,
    require_quality: bool = True,
) -> list[RiskMatch]:
    pair_map = {
        (pair.reference_id, pair.generated_id): pair
        for pair in judge.pair_evaluations
    }
    matches: list[RiskMatch] = []
    for reference_id, generated_id in (
        select_match_ids(
            scenario,
            generated,
            judge,
            threshold=threshold,
        )
    ):
        pair = pair_map[
            (reference_id, generated_id)
        ]
        if (
            require_quality
            and not pair.quality_evaluated
        ):
            raise ValueError(
                "Matched pair is missing "
                "quality evaluation: "
                f"{reference_id}/{generated_id}"
            )
        matches.append(
            RiskMatch(
                reference_id=reference_id,
                generated_id=generated_id,
                semantic_match=(
                    pair.semantic_match
                ),
                accident_type_correctness=(
                    pair
                    .accident_type_correctness
                ),
                mitigation_appropriateness=(
                    pair
                    .mitigation_appropriateness
                ),
                mitigation_specificity=(
                    pair
                    .mitigation_specificity
                ),
                legal_basis_relevance=(
                    pair
                    .legal_basis_relevance
                ),
            )
        )
    return matches
