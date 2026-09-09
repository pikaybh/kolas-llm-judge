from kolas_llm_judge.identification import (
    HAZARD_IDENTIFICATION_RULE,
    hazard_identification_metric,
    pair_identifies_reference,
)


def row(*, same: bool, context: bool, accident: bool, reference_id: str = "r1"):
    return {
        "reference_id": reference_id,
        "generated_id": "g1",
        "same_hazard_mechanism": same,
        "context_compatible": context,
        "accident_compatible": accident,
    }


def test_identification_rule_is_frozen_or_expression() -> None:
    assert HAZARD_IDENTIFICATION_RULE == (
        "(same_hazard_mechanism AND context_compatible) OR accident_compatible"
    )
    assert pair_identifies_reference(row(same=True, context=True, accident=False))
    assert pair_identifies_reference(row(same=False, context=False, accident=True))
    assert not pair_identifies_reference(row(same=True, context=False, accident=False))
    assert not pair_identifies_reference(row(same=False, context=True, accident=False))


def test_identification_is_many_to_one_by_reference() -> None:
    matrix = [
        row(same=True, context=True, accident=True, reference_id="r1"),
        row(same=True, context=True, accident=True, reference_id="r2"),
    ]
    metric = hazard_identification_metric(matrix, ["r1", "r2", "r3"])
    assert metric.numerator == 2
    assert metric.denominator == 3
    assert metric.rate == 2 / 3
