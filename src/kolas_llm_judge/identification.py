from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import MetricValue


HAZARD_IDENTIFICATION_RULE_VERSION = "hazard-identification-v1"
HAZARD_IDENTIFICATION_RULE = (
    "(same_hazard_mechanism AND context_compatible) OR accident_compatible"
)
HAZARD_IDENTIFICATION_DENOMINATOR = "references_with_completed_binary_match_matrix"


def _value(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name)


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
