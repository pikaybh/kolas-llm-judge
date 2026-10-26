from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import MetricValue


HAZARD_SEMANTIC_IDENTIFICATION_RULE_VERSION = "hazard-semantic-identification-v1"
HAZARD_SEMANTIC_IDENTIFICATION_RULE = "same_hazard_mechanism AND context_compatible"
HAZARD_SEMANTIC_IDENTIFICATION_DENOMINATOR = (
    "references_with_completed_binary_match_matrix"
)

# Supplementary KPI-compatible metric retained for continuity with earlier project KPIs.
# It is intentionally broader than the KOLAS primary semantic-identification measurand.
HAZARD_IDENTIFICATION_RULE_VERSION = "hazard-identification-v1"
HAZARD_IDENTIFICATION_RULE = (
    "(same_hazard_mechanism AND context_compatible) OR accident_compatible"
)
HAZARD_IDENTIFICATION_DENOMINATOR = "references_with_completed_binary_match_matrix"


def _value(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name)



def pair_semantically_identifies_reference(row: Any) -> bool:
    """Strict semantic reference identification diagnostic.

    Accident-class compatibility alone never establishes identification. The generated
    risk must express the same hazardous mechanism in a compatible work/exposure context.
    """
    return bool(
        bool(_value(row, "same_hazard_mechanism"))
        and bool(_value(row, "context_compatible"))
    )


def semantically_identified_reference_ids(matrix: Iterable[Any]) -> set[str]:
    return {
        str(_value(row, "reference_id"))
        for row in matrix
        if pair_semantically_identifies_reference(row)
    }


def hazard_semantic_identification_metric(
    matrix: Iterable[Any],
    reference_ids: Iterable[str],
) -> MetricValue:
    references = list(dict.fromkeys(str(x) for x in reference_ids))
    identified = semantically_identified_reference_ids(matrix)
    numerator = sum(reference_id in identified for reference_id in references)
    denominator = len(references)
    return MetricValue(
        numerator=numerator,
        denominator=denominator,
        rate=(numerator / denominator) if denominator else None,
    )

def pair_identifies_reference(row: Any) -> bool:
    """Return whether a single reference-generated pair identifies the reference.

    This KPI-oriented rule is deliberately broader than strict 1:1 reference
    coverage. It credits either a direct hazard-mechanism match in compatible
    context, or a safety-engineering-compatible accident/damage mechanism.
    """
    return bool(
        (
            bool(_value(row, "same_hazard_mechanism"))
            and bool(_value(row, "context_compatible"))
        )
        or bool(_value(row, "accident_compatible"))
    )


def identified_reference_ids(matrix: Iterable[Any]) -> set[str]:
    return {
        str(_value(row, "reference_id"))
        for row in matrix
        if pair_identifies_reference(row)
    }


def hazard_identification_metric(
    matrix: Iterable[Any],
    reference_ids: Iterable[str],
) -> MetricValue:
    references = list(dict.fromkeys(str(x) for x in reference_ids))
    identified = identified_reference_ids(matrix)
    numerator = sum(reference_id in identified for reference_id in references)
    denominator = len(references)
    return MetricValue(
        numerator=numerator,
        denominator=denominator,
        rate=(numerator / denominator) if denominator else None,
    )
