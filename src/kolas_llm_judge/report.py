from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, load_json


METRIC_NAMES = [
    "reference_risk_coverage",
    "unsupported_risk_rate",
    "accident_type_correctness",
    "mitigation_appropriateness",
    "mitigation_specificity",
    "legal_basis_presence",
    "legal_basis_relevance",
    "critical_safety_error_rate",
]


def _wilson_interval(
    numerator: int,
    denominator: int,
    z: float = 1.959963984540054,
) -> tuple[float | None, float | None]:
    if denominator <= 0:
        return None, None
    p = numerator / denominator
    z2 = z * z
    center = (
        p + z2 / (2 * denominator)
    ) / (1 + z2 / denominator)
    half = (
        z
        * math.sqrt(
            p * (1 - p) / denominator
            + z2
            / (
                4
                * denominator
                * denominator
            )
        )
        / (1 + z2 / denominator)
    )
    return (
        max(0.0, center - half),
        min(1.0, center + half),
    )


def _percentile(
    values: list[float],
    q: float,
) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (
        (len(ordered) - 1) * q
    )
    low_index = math.floor(position)
    high_index = math.ceil(position)
    if low_index == high_index:
        return ordered[low_index]
    fraction = position - low_index
    return (
        ordered[low_index]
        + (
            ordered[high_index]
            - ordered[low_index]
        )
        * fraction
    )


def _aggregate_metric(
    results: list[dict[str, Any]],
    name: str,
) -> dict[str, Any]:
    numerator = 0
    denominator = 0
    case_rates: list[float] = []
    for result in results:
        metric = (
            result.get("metrics", {})
            .get(name, {})
        )
        numerator += int(
            metric.get("numerator") or 0
        )
        denominator += int(
            metric.get("denominator") or 0
        )
        rate = metric.get("rate")
        if isinstance(
            rate,
            (int, float),
        ):
            case_rates.append(float(rate))
    low, high = _wilson_interval(
        numerator,
        denominator,
    )
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": (
            numerator / denominator
            if denominator
            else None
        ),
        "ci95_wilson_low": low,
        "ci95_wilson_high": high,
        "case_macro_mean": (
            statistics.fmean(case_rates)
            if case_rates
            else None
        ),
        "case_macro_stdev": (
            statistics.stdev(case_rates)
            if len(case_rates) > 1
            else (
                0.0
                if case_rates
                else None
            )
        ),
        "case_count": len(case_rates),
    }


def _aggregate_bool_check(
    results: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    values: list[bool] = []
    for result in results:
        checks = (
            result.get(
                "deterministic",
                {},
            ).get("checks", [])
        )
        for check in checks:
            value = check.get(field)
            if isinstance(value, bool):
                values.append(value)
    passed = sum(values)
    low, high = _wilson_interval(
        passed,
        len(values),
    )
    return {
        "numerator": passed,
        "denominator": len(values),
        "rate": (
            passed / len(values)
            if values
            else None
        ),
        "ci95_wilson_low": low,
        "ci95_wilson_high": high,
    }


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _usage_token(
    usage: dict[str, Any],
    key: str,
) -> int:
    return _safe_int(usage.get(key))


def _usage_nested_token(
    usage: dict[str, Any],
    parent: str,
    key: str,
) -> int:
    details = usage.get(parent)
    if not isinstance(details, dict):
        return 0
    return _safe_int(details.get(key))


def _judge_usage_for_result(
    result: dict[str, Any],
) -> dict[str, int]:
    judge = result.get("judge", {})
    if not isinstance(judge, dict):
        return {
            "call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
            "cached_input_tokens": 0,
        }

    calls_raw = judge.get("calls")
    usage_entries: list[
        dict[str, Any]
    ] = []
    call_count = 0

    if isinstance(calls_raw, list):
        call_count = len(calls_raw)
        for call in calls_raw:
            if not isinstance(call, dict):
                continue
            usage = call.get("usage")
            if isinstance(usage, dict):
                usage_entries.append(usage)

    if not calls_raw:
        usage = judge.get("usage")
        if isinstance(usage, dict):
            nested_calls = usage.get(
                "calls"
            )
            if isinstance(
                nested_calls,
                list,
            ):
                call_count = max(
                    _safe_int(
                        usage.get(
                            "call_count"
                        )
                    ),
                    len(nested_calls),
                )
                usage_entries.extend(
                    entry
                    for entry
                    in nested_calls
                    if isinstance(
                        entry,
                        dict,
                    )
                )
            else:
                call_count = 1
                usage_entries.append(usage)

    input_tokens = sum(
        _usage_token(
            usage,
            "input_tokens",
        )
        for usage in usage_entries
    )
    output_tokens = sum(
        _usage_token(
            usage,
            "output_tokens",
        )
        for usage in usage_entries
    )
    total_tokens = sum(
        _usage_token(
            usage,
            "total_tokens",
        )
        for usage in usage_entries
    )
    reasoning_tokens = sum(
        _usage_nested_token(
            usage,
            "output_tokens_details",
            "reasoning_tokens",
        )
        for usage in usage_entries
    )
    cached_input_tokens = sum(
        _usage_nested_token(
            usage,
            "input_tokens_details",
            "cached_tokens",
        )
        for usage in usage_entries
    )

    if (
        total_tokens == 0
        and (
            input_tokens
            or output_tokens
        )
    ):
        total_tokens = (
            input_tokens
            + output_tokens
        )

    return {
        "call_count": call_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "reasoning_tokens": (
            reasoning_tokens
        ),
        "cached_input_tokens": (
            cached_input_tokens
        ),
    }


def _aggregate_sut_runtime(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    latencies = [
        float(
            result.get("sut", {})
            .get("elapsed_ms")
        )
        for result in results
        if isinstance(
            result.get("sut", {})
            .get("elapsed_ms"),
            (int, float),
        )
    ]
    create_run_retries = sum(
        max(
            0,
            _safe_int(
                result.get("sut", {})
                .get(
                    "create_run_attempts",
                    1,
                )
            )
            - 1,
        )
        for result in results
    )
    stream_reconnects = sum(
        _safe_int(
            result.get("sut", {})
            .get(
                "stream_reconnects",
                0,
            )
        )
        for result in results
    )
    auth_recoveries = sum(
        _safe_int(
            result.get("sut", {}).get(
                "auth_recoveries",
                0,
            )
        )
        for result in results
    )
    retry_counts = [
        max(
            0,
            _safe_int(
                result.get("sut", {})
                .get(
                    "retry_count",
                    max(
                        0,
                        _safe_int(
                            result.get(
                                "sut",
                                {},
                            ).get(
                                "create_run_attempts",
                                1,
                            )
                        )
                        - 1,
                    )
                    + _safe_int(
                        result.get(
                            "sut",
                            {},
                        ).get(
                            "stream_reconnects",
                            0,
                        )
                    )
                    + _safe_int(
                        result.get(
                            "sut",
                            {},
                        ).get(
                            "auth_recoveries",
                            0,
                        )
                    ),
                )
            ),
        )
        for result in results
    ]
    cases_with_retry = sum(
        count > 0
        for count in retry_counts
    )
    low, high = _wilson_interval(
        cases_with_retry,
        len(results),
    )
    return {
        "latency_ms": {
            "case_count": len(
                latencies
            ),
            "mean": (
                statistics.fmean(
                    latencies
                )
                if latencies
                else None
            ),
            "median": (
                statistics.median(
                    latencies
                )
                if latencies
                else None
            ),
            "p95": _percentile(
                latencies,
                0.95,
            ),
            "min": (
                min(latencies)
                if latencies
                else None
            ),
            "max": (
                max(latencies)
                if latencies
                else None
            ),
        },
        "retries": {
            "case_count": len(results),
            "cases_with_retry": (
                cases_with_retry
            ),
            "case_rate": (
                cases_with_retry
                / len(results)
                if results
                else None
            ),
            "case_rate_ci95_wilson_low": (
                low
            ),
            "case_rate_ci95_wilson_high": (
                high
            ),
            "total_retry_count": sum(
                retry_counts
            ),
            "create_run_retry_count": (
                create_run_retries
            ),
            "stream_reconnect_count": (
                stream_reconnects
            ),
            "auth_recovery_count": (
                auth_recoveries
            ),
            "max_retry_count_per_case": (
                max(retry_counts)
                if retry_counts
                else 0
            ),
        },
    }


def _aggregate_judge_usage(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    case_usage = [
        _judge_usage_for_result(
            result
        )
        for result in results
    ]
    totals = {
        key: sum(
            row[key]
            for row in case_usage
        )
        for key in [
            "call_count",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "reasoning_tokens",
            "cached_input_tokens",
        ]
    }
    with_usage = sum(
        row["call_count"] > 0
        for row in case_usage
    )
    return {
        "case_count": len(results),
        "cases_with_usage": (
            with_usage
        ),
        **totals,
        "calls_per_case_mean": (
            totals["call_count"]
            / len(results)
            if results
            else None
        ),
        "tokens_per_case_mean": (
            totals["total_tokens"]
            / len(results)
            if results
            else None
        ),
    }


def collect_case_results(
    run_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    completed: list[
        dict[str, Any]
    ] = []
    failed: list[
        dict[str, Any]
    ] = []
    cases_dir = run_dir / "cases"
    if not cases_dir.exists():
        return completed, failed
    for case_dir in sorted(
        path
        for path in cases_dir.iterdir()
        if path.is_dir()
    ):
        result_path = (
            case_dir / "result.json"
        )
        error_path = (
            case_dir / "error.json"
        )
        if result_path.exists():
            completed.append(
                load_json(result_path)
            )
        elif error_path.exists():
            failed.append(
                load_json(error_path)
            )
    return completed, failed


def build_summary(
    run_dir: Path,
) -> dict[str, Any]:
    manifest = load_json(
        run_dir / "manifest.json"
    )
    completion_path = (
        run_dir / "completion.json"
    )
    completion = (
        load_json(completion_path)
        if completion_path.exists()
        else {}
    )
    completed, failed = (
        collect_case_results(run_dir)
    )
    selected = int(
        manifest["selected_case_count"]
    )

    total_generated = sum(
        len(
            result.get(
                "parsed",
                {},
            ).get("risks", [])
        )
        for result in completed
    )
    schema_valid = sum(
        int(
            result.get(
                "deterministic",
                {},
            ).get(
                "schema_valid_items"
            )
            or 0
        )
        for result in completed
    )
    xml_success = sum(
        bool(
            result.get(
                "deterministic",
                {},
            ).get(
                "xml_parse_success"
            )
        )
        for result in completed
    )

    summary = {
        "run_id": manifest["run_id"],
        "mode": manifest["mode"],
        "selected_cases": selected,
        "completed_cases": len(
            completed
        ),
        "failed_cases": len(failed),
        "pending_cases": max(
            0,
            selected
            - len(completed)
            - len(failed),
        ),
        "sut_case_success_rate": (
            len(completed) / selected
            if selected
            else None
        ),
        "sut_source_stable": (
            completion.get(
                "sut_source_stable"
            )
        ),
        "calibration_gate_pass": (
            (
                manifest.get(
                    "calibration"
                )
                or {}
            ).get("gate_pass")
        ),
        "official_candidate_valid": bool(
            manifest.get("mode")
            == "full"
            and len(completed)
            == selected
            and not failed
            and completion.get(
                "sut_source_stable"
            )
            is True
            and (
                manifest.get(
                    "calibration"
                )
                or {}
            ).get("gate_pass")
            is True
            and (
                manifest.get(
                    "calibration"
                )
                or {}
            ).get(
                "method_identity_match"
            )
            is True
            and bool(
                (
                    manifest.get("git")
                    or {}
                ).get("head")
            )
            and not bool(
                (
                    manifest.get("git")
                    or {}
                ).get("dirty")
            )
        ),
        "sut_runtime": (
            _aggregate_sut_runtime(
                completed
            )
        ),
        "judge_usage": (
            _aggregate_judge_usage(
                completed
            )
        ),
        "xml_parse_success": {
            "numerator": (
                xml_success
            ),
            "denominator": len(
                completed
            ),
            "rate": (
                xml_success
                / len(completed)
                if completed
                else None
            ),
        },
        "schema_compliance": {
            "numerator": (
                schema_valid
            ),
            "denominator": (
                total_generated
            ),
            "rate": (
                schema_valid
                / total_generated
                if total_generated
                else None
            ),
            "ci95_wilson_low": (
                _wilson_interval(
                    schema_valid,
                    total_generated,
                )[0]
            ),
            "ci95_wilson_high": (
                _wilson_interval(
                    schema_valid,
                    total_generated,
                )[1]
            ),
        },
        "deterministic_checks": {
            field: _aggregate_bool_check(
                completed,
                field,
            )
            for field in [
                "frequency_in_range",
                "severity_in_range",
                "score_math_correct",
                "post_frequency_in_range",
                "post_severity_in_range",
                "post_score_math_correct",
                "post_risk_nonincreasing",
            ]
        },
        "metrics": {
            name: _aggregate_metric(
                completed,
                name,
            )
            for name in METRIC_NAMES
        },
    }
    return summary


def export_reports(
    run_dir: Path,
) -> dict[str, Path]:
    completed, failed = (
        collect_case_results(run_dir)
    )
    summary = build_summary(run_dir)
    report_dir = run_dir / "report"
    report_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_path = (
        report_dir / "summary.json"
    )
    atomic_write_json(
        summary_path,
        summary,
    )

    cases_csv = (
        report_dir
        / "case_metrics.csv"
    )
    with cases_csv.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        fieldnames = [
            "case_id",
            "process",
            "subprocess",
            "generated_count",
            "reference_count",
            "elapsed_ms",
            "retry_count",
            "create_run_attempts",
            "stream_reconnects",
            "auth_recoveries",
            "judge_call_count",
            "judge_input_tokens",
            "judge_output_tokens",
            "judge_total_tokens",
            "judge_reasoning_tokens",
            "judge_cached_input_tokens",
            *[
                f"{name}_num"
                for name in METRIC_NAMES
            ],
            *[
                f"{name}_den"
                for name in METRIC_NAMES
            ],
            *[
                f"{name}_rate"
                for name in METRIC_NAMES
            ],
        ]
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        for result in completed:
            sut = result.get(
                "sut",
                {},
            )
            usage = (
                _judge_usage_for_result(
                    result
                )
            )
            row: dict[str, Any] = {
                "case_id": (
                    result["case_id"]
                ),
                "process": (
                    result.get(
                        "scenario_input",
                        {},
                    ).get("process")
                ),
                "subprocess": (
                    result.get(
                        "scenario_input",
                        {},
                    ).get(
                        "subprocess"
                    )
                ),
                "generated_count": len(
                    result.get(
                        "parsed",
                        {},
                    ).get(
                        "risks",
                        [],
                    )
                ),
                "reference_count": (
                    result.get(
                        "reference_count"
                    )
                ),
                "elapsed_ms": (
                    sut.get(
                        "elapsed_ms"
                    )
                ),
                "retry_count": (
                    sut.get(
                        "retry_count",
                        0,
                    )
                ),
                "create_run_attempts": (
                    sut.get(
                        "create_run_attempts",
                        1,
                    )
                ),
                "stream_reconnects": (
                    sut.get(
                        "stream_reconnects",
                        0,
                    )
                ),
                "auth_recoveries": (
                    sut.get(
                        "auth_recoveries",
                        0,
                    )
                ),
                "judge_call_count": (
                    usage["call_count"]
                ),
                "judge_input_tokens": (
                    usage["input_tokens"]
                ),
                "judge_output_tokens": (
                    usage["output_tokens"]
                ),
                "judge_total_tokens": (
                    usage["total_tokens"]
                ),
                "judge_reasoning_tokens": (
                    usage[
                        "reasoning_tokens"
                    ]
                ),
                "judge_cached_input_tokens": (
                    usage[
                        "cached_input_tokens"
                    ]
                ),
            }
            for name in METRIC_NAMES:
                metric = (
                    result.get(
                        "metrics",
                        {},
                    ).get(name, {})
                )
                row[
                    f"{name}_num"
                ] = metric.get(
                    "numerator"
                )
                row[
                    f"{name}_den"
                ] = metric.get(
                    "denominator"
                )
                row[
                    f"{name}_rate"
                ] = metric.get("rate")
            writer.writerow(row)

    failures_csv = (
        report_dir / "failures.csv"
    )
    with failures_csv.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id",
                "stage",
                "error_type",
                "error",
                "updated_at_utc",
            ],
        )
        writer.writeheader()
        for failure in failed:
            writer.writerow(
                {
                    key: failure.get(
                        key
                    )
                    for key in [
                        "case_id",
                        "stage",
                        "error_type",
                        "error",
                        "updated_at_utc",
                    ]
                }
            )

    return {
        "summary": summary_path,
        "cases_csv": cases_csv,
        "failures_csv": (
            failures_csv
        ),
    }
