from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from .models import CaseJudgeResult, EvaluationScenario, GeneratedRisk, RiskMatch


def match_risks(
    scenario: EvaluationScenario,
    generated: list[GeneratedRisk],
    judge: CaseJudgeResult,
    *,
    threshold: int = 3,
) -> list[RiskMatch]:
    if not scenario.references or not generated:
        return []

    pair_map = {(p.reference_id, p.generated_id): p for p in judge.pair_evaluations}
    weights = np.zeros((len(scenario.references), len(generated)), dtype=np.int64)
    for i, reference in enumerate(scenario.references):
        for j, risk in enumerate(generated):
            pair = pair_map.get((reference.reference_id, risk.generated_id))
            if pair is None:
                raise ValueError(f"Missing pair score: {reference.reference_id}/{risk.generated_id}")
            if pair.semantic_match >= threshold:
                # Semantic match dominates all secondary qualities. Stable source/output order
                # resolves exact ties deterministically with the locked scipy version.
                weights[i, j] = (
                    pair.semantic_match * 1_000_000
                    + pair.accident_type_correctness * 10_000
                    + pair.mitigation_appropriateness * 1_000
                    + pair.mitigation_specificity * 100
                    + pair.legal_basis_relevance * 10
                )

    rows, cols = linear_sum_assignment(weights, maximize=True)
    matches: list[RiskMatch] = []
    for row, col in zip(rows.tolist(), cols.tolist()):
        if weights[row, col] <= 0:
            continue
        reference = scenario.references[row]
        risk = generated[col]
        pair = pair_map[(reference.reference_id, risk.generated_id)]
        if pair.semantic_match < threshold:
            continue
        matches.append(RiskMatch(
            reference_id=reference.reference_id,
            generated_id=risk.generated_id,
            semantic_match=pair.semantic_match,
            accident_type_correctness=pair.accident_type_correctness,
            mitigation_appropriateness=pair.mitigation_appropriateness,
            mitigation_specificity=pair.mitigation_specificity,
            legal_basis_relevance=pair.legal_basis_relevance,
        ))
    return matches
