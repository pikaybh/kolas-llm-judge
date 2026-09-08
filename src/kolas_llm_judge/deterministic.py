from __future__ import annotations

from .models import (
    DeterministicAssessmentResult,
    DeterministicRiskCheck,
    ParsedRiskAssessment,
)


def _ranges(method: str | None) -> tuple[range | None, range | None]:
    normalized = (method or "").strip()
    if normalized == "빈도강도법 5x4":
        return range(1, 6), range(1, 5)
    if normalized == "빈도강도법 4x3":
        return range(1, 5), range(1, 4)
    if normalized == "빈도강도법 3x3":
        return range(1, 4), range(1, 4)
    return None, None


def _verbal_rank(value: str | None) -> int | None:
    if not value:
        return None
    normalized = value.strip()
    return {"하": 1, "중": 2, "상": 3}.get(normalized)


def evaluate_deterministic(
    parsed: ParsedRiskAssessment,
) -> DeterministicAssessmentResult:
    frequency_range, severity_range = _ranges(parsed.method)
    checks: list[DeterministicRiskCheck] = []

    for risk in parsed.risks:
        errors: list[str] = []
        schema_valid = bool(
            risk.hazard.strip() and risk.mitigation and risk.accident_types
        )
        if not risk.hazard.strip():
            errors.append("missing_hazard")
        if not risk.accident_types:
            errors.append("missing_accident_classification")
        if not risk.mitigation:
            errors.append("missing_mitigation")

        frequency_ok = None
        severity_ok = None
        math_ok = None
        post_frequency_ok = None
        post_severity_ok = None
        post_math_ok = None
        post_nonincreasing = None

        if frequency_range is not None and severity_range is not None:
            frequency_ok = (
                risk.likelihood in frequency_range
                if risk.likelihood is not None
                else False
            )
            severity_ok = (
                risk.severity in severity_range
                if risk.severity is not None
                else False
            )
            if risk.likelihood is None:
                errors.append("missing_frequency")
                schema_valid = False
            elif not frequency_ok:
                errors.append("frequency_out_of_range")
            if risk.severity is None:
                errors.append("missing_severity")
                schema_valid = False
            elif not severity_ok:
                errors.append("severity_out_of_range")

            if risk.risk_score is None:
                math_ok = False
                schema_valid = False
                errors.append("missing_risk_score")
            elif risk.likelihood is None or risk.severity is None:
                math_ok = False
            else:
                math_ok = (
                    risk.risk_score == risk.likelihood * risk.severity
                )
                if not math_ok:
                    errors.append("risk_score_math_mismatch")

            post_frequency_ok = (
                risk.post_likelihood in frequency_range
                if risk.post_likelihood is not None
                else False
            )
            post_severity_ok = (
                risk.post_severity in severity_range
                if risk.post_severity is not None
                else False
            )
            if risk.post_likelihood is None:
                errors.append("missing_post_frequency")
                schema_valid = False
            elif not post_frequency_ok:
                errors.append("post_frequency_out_of_range")
            if risk.post_severity is None:
                errors.append("missing_post_severity")
                schema_valid = False
            elif not post_severity_ok:
                errors.append("post_severity_out_of_range")

            if risk.post_risk_score is None:
                post_math_ok = False
                post_nonincreasing = False
                schema_valid = False
                errors.append("missing_post_risk_score")
            elif (
                risk.post_likelihood is None
                or risk.post_severity is None
            ):
                post_math_ok = False
                post_nonincreasing = False
            else:
                post_math_ok = (
                    risk.post_risk_score
                    == risk.post_likelihood * risk.post_severity
                )
                if not post_math_ok:
                    errors.append("post_risk_score_math_mismatch")
                if risk.risk_score is not None:
                    post_nonincreasing = (
                        risk.post_risk_score <= risk.risk_score
                    )
                    if not post_nonincreasing:
                        errors.append("post_risk_increased")
        else:
            initial_rank = _verbal_rank(risk.risk_level_verbal)
            post_rank = _verbal_rank(risk.post_risk_level_verbal)
            if parsed.method in {"3단계 판단법", "체크리스트법"}:
                if initial_rank is None:
                    schema_valid = False
                    errors.append("missing_or_invalid_risk_level_verbal")
                if post_rank is None:
                    schema_valid = False
                    errors.append(
                        "missing_or_invalid_post_risk_level_verbal"
                    )
                if initial_rank is not None and post_rank is not None:
                    post_nonincreasing = post_rank <= initial_rank
                    if not post_nonincreasing:
                        errors.append("post_risk_increased")

        checks.append(
            DeterministicRiskCheck(
                generated_id=risk.generated_id,
                schema_valid=schema_valid,
                frequency_in_range=frequency_ok,
                severity_in_range=severity_ok,
                score_math_correct=math_ok,
                post_frequency_in_range=post_frequency_ok,
                post_severity_in_range=post_severity_ok,
                post_score_math_correct=post_math_ok,
                post_risk_nonincreasing=post_nonincreasing,
                errors=errors,
            )
        )

    errors: list[str] = []
    if not parsed.risks:
        errors.append("no_risk_items")
    if not parsed.method:
        errors.append("missing_method")
    return DeterministicAssessmentResult(
        xml_parse_success=True,
        method=parsed.method,
        item_count=len(parsed.risks),
        schema_valid_items=sum(
            check.schema_valid for check in checks
        ),
        checks=checks,
        errors=errors,
    )
