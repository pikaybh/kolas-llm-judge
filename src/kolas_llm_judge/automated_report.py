from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from statistics import fmean, median
from typing import Any

import numpy as np

from .identification import (
    identified_reference_ids,
    semantically_identified_reference_ids,
)
from .io_utils import atomic_write_json, load_json


METRIC_NAMES = (
    "hazard_semantic_identification_recall",
    "hazard_identification_accuracy",
    "reference_risk_coverage",
    "accident_classification_agreement",
    "mitigation_appropriateness",
    "mitigation_actionability",
    "mitigation_specificity",
    "legal_basis_presence",
    "legal_basis_relevance",
    "unsafe_advice_rate",
    "critical_safety_error_rate",
)


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _latency_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "min": None,
            "max": None,
        }
    return {
        "count": len(values),
        "mean": fmean(values),
        "median": median(values),
        "p90": _percentile(values, 90),
        "p95": _percentile(values, 95),
        "p99": _percentile(values, 99),
        "min": min(values),
        "max": max(values),
    }


def _sum_usage(calls: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "call_count": len(calls),
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "reasoning_tokens": 0,
        "cached_input_tokens": 0,
        "response_models": {},
    }
    models: Counter[str] = Counter()
    for call in calls:
        usage = call.get("usage") or {}
        result["input_tokens"] += int(usage.get("input_tokens") or 0)
        result["output_tokens"] += int(usage.get("output_tokens") or 0)
        result["total_tokens"] += int(usage.get("total_tokens") or 0)
        result["reasoning_tokens"] += int(
            (usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0
        )
        result["cached_input_tokens"] += int(
            (usage.get("input_tokens_details") or {}).get("cached_tokens") or 0
        )
        model = call.get("response_model")
        if model:
            models[str(model)] += 1
    result["response_models"] = dict(sorted(models.items()))
    return result


def _deterministic_micro(results: list[dict[str, Any]]) -> dict[str, Any]:
    schema_n = 0
    schema_d = 0
    fields = {
        "frequency_in_range": [0, 0],
        "severity_in_range": [0, 0],
        "score_math_correct": [0, 0],
        "post_frequency_in_range": [0, 0],
        "post_severity_in_range": [0, 0],
        "post_score_math_correct": [0, 0],
        "post_risk_nonincreasing": [0, 0],
    }
    post_modes: Counter[str] = Counter()
    for result in results:
        det = result.get("deterministic") or {}
        schema_n += int(det.get("schema_valid_items") or 0)
        schema_d += int(det.get("item_count") or 0)
        post_modes[str(det.get("post_improvement_mode") or "unknown")] += 1
        for check in det.get("checks") or []:
            for name in fields:
                value = check.get(name)
                if isinstance(value, bool):
                    fields[name][1] += 1
                    fields[name][0] += int(value)
    return {
        "schema_compliance": _ratio(schema_n, schema_d),
        "checks": {
            name: _ratio(values[0], values[1])
            for name, values in fields.items()
        },
        "post_improvement_mode_counts": dict(sorted(post_modes.items())),
    }


def _case_metric(
    run_dir: Path,
    result: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    metric = (result.get("metrics") or {}).get(name)
    if metric is not None:
        return metric
    if name not in {
        "hazard_semantic_identification_recall",
        "hazard_identification_accuracy",
    }:
        return {}

    judge_path = run_dir / "cases" / str(result.get("case_id")) / "binary_judge.json"
    if not judge_path.exists():
        return {}
    evaluation = load_json(judge_path).get("evaluation") or {}
    matrix = list(evaluation.get("match_matrix") or [])
    reference_ids = {str(row.get("reference_id")) for row in matrix if row.get("reference_id")}
    if not reference_ids:
        return {}
    identified = (
        semantically_identified_reference_ids(matrix)
        if name == "hazard_semantic_identification_recall"
        else identified_reference_ids(matrix)
    )
    return _ratio(
        len(reference_ids & identified),
        len(reference_ids),
    )


def _metric_micro(
    results: list[dict[str, Any]],
    run_dir: Path,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for name in METRIC_NAMES:
        numerator = 0
        denominator = 0
        for result in results:
            metric = _case_metric(run_dir, result, name)
            numerator += int(metric.get("numerator") or 0)
            denominator += int(metric.get("denominator") or 0)
        output[name] = _ratio(numerator, denominator)
    return output


def collect_automated_report(run_dir: Path) -> dict[str, Any]:
    manifest = load_json(run_dir / "manifest.json")
    selected = int(manifest.get("selected_case_count") or 0)
    results = [
        load_json(path)
        for path in sorted((run_dir / "cases").glob("*/result.json"))
    ]
    errors = [
        load_json(path)
        for path in sorted((run_dir / "cases").glob("*/error.json"))
        if not (path.parent / "result.json").exists()
    ]
    processed = len(results) + len(errors)

    failure_classes = Counter(str(row.get("failure_class") or "unknown") for row in errors)
    failure_reasons = Counter(str(row.get("failure_reason") or "unknown") for row in errors)
    failure_stages = Counter(str(row.get("stage") or "unknown") for row in errors)

    sut_latencies: list[float] = []
    retry_events = 0
    stream_reconnects = 0
    create_run_retries = 0
    for sut_path in sorted((run_dir / "cases").glob("*/sut.json")):
        sut = load_json(sut_path)
        if isinstance(sut.get("elapsed_ms"), (int, float)):
            sut_latencies.append(float(sut["elapsed_ms"]))
        create_attempts = int(sut.get("create_run_attempts") or 1)
        create_run_retries += max(0, create_attempts - 1)
        reconnect = int(sut.get("stream_reconnects") or 0)
        stream_reconnects += reconnect
        retry_events += max(0, create_attempts - 1) + reconnect

    judge_calls: list[dict[str, Any]] = []
    generated_counts: list[int] = []
    for result in results:
        generated_counts.append(int(result.get("generated_count") or 0))
        judge_path = run_dir / "cases" / str(result["case_id"]) / "binary_judge.json"
        if judge_path.exists():
            evaluation = (load_json(judge_path).get("evaluation") or {})
            judge_calls.extend(evaluation.get("calls") or [])

    completion_path = run_dir / "completion.json"
    completion = load_json(completion_path) if completion_path.exists() else {}
    qualification = manifest.get("qualification") or {}
    source_stable = completion.get("sut_source_stable")
    if source_stable is None:
        source_stable = manifest.get("sut_source_stable")

    infrastructure_failures = (
        failure_classes.get("evaluator_failure", 0)
        + failure_classes.get("infrastructure_failure", 0)
    )
    procedure_valid = bool(
        processed == selected
        and qualification.get("gate_pass") is True
        and source_stable is True
        and infrastructure_failures == 0
    )

    return {
        "protocol": "automated-kolas-v1",
        "run_id": manifest.get("run_id"),
        "mode": manifest.get("mode"),
        "selected_cases": selected,
        "processed_cases": processed,
        "completed_cases": len(results),
        "failed_cases": len(errors),
        "sut_completion_rate": _ratio(len(results), selected),
        "failure_classes": dict(sorted(failure_classes.items())),
        "failure_reasons": dict(sorted(failure_reasons.items())),
        "failure_stages": dict(sorted(failure_stages.items())),
        "deterministic": _deterministic_micro(results),
        "measurement_policy": {
            "primary_metric": "hazard_semantic_identification_recall",
            "primary_rule": "same_hazard_mechanism AND context_compatible",
            "supplementary_kpi_metric": "hazard_identification_accuracy",
            "performance_decision": "report_only_until_testing_lab_approval",
        },
        "metrics": _metric_micro(results, run_dir),
        "sut_runtime": {
            "latency_ms": _latency_stats(sut_latencies),
            "create_run_retry_count": create_run_retries,
            "stream_reconnect_count": stream_reconnects,
            "retry_count": retry_events,
            "global_auth_recovery_count": completion.get("auth_recovery_count"),
        },
        "judge_usage": _sum_usage(judge_calls),
        "generated_risks": {
            "total": sum(generated_counts),
            "mean_per_completed_case": (
                fmean(generated_counts) if generated_counts else None
            ),
            "median_per_completed_case": (
                median(generated_counts) if generated_counts else None
            ),
            "max_per_completed_case": max(generated_counts) if generated_counts else None,
        },
        "qualification": qualification,
        "sut_source_stable": source_stable,
        "evaluator_or_infrastructure_failure_count": infrastructure_failures,
        "procedure_valid": procedure_valid,
        "note": (
            "sut_non_completion is a measured SUT outcome and does not by itself invalidate "
            "the test procedure. evaluator/infrastructure failures do invalidate the candidate."
        ),
    }


def export_automated_report(run_dir: Path) -> dict[str, Path]:
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = collect_automated_report(run_dir)
    summary_path = report_dir / "summary.json"
    cases_path = report_dir / "case_metrics.csv"
    failures_path = report_dir / "failures.csv"
    atomic_write_json(summary_path, summary)

    case_fields = [
        "case_id",
        "process",
        "subprocess",
        "reference_count",
        "generated_count",
        "sut_elapsed_ms",
        *METRIC_NAMES,
    ]
    with cases_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=case_fields)
        writer.writeheader()
        for result_path in sorted((run_dir / "cases").glob("*/result.json")):
            row = load_json(result_path)
            metrics = row.get("metrics") or {}
            writer.writerow(
                {
                    "case_id": row.get("case_id"),
                    "process": (row.get("scenario_input") or {}).get("process"),
                    "subprocess": (row.get("scenario_input") or {}).get("subprocess"),
                    "reference_count": row.get("reference_count"),
                    "generated_count": row.get("generated_count"),
                    "sut_elapsed_ms": (row.get("sut") or {}).get("elapsed_ms"),
                    **{
                        name: _case_metric(run_dir, row, name).get("rate")
                        for name in METRIC_NAMES
                    },
                }
            )

    failure_fields = [
        "case_id",
        "stage",
        "failure_class",
        "failure_reason",
        "error_type",
        "error",
        "failed_at_utc",
    ]
    with failures_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=failure_fields)
        writer.writeheader()
        for error_path in sorted((run_dir / "cases").glob("*/error.json")):
            if (error_path.parent / "result.json").exists():
                continue
            row = load_json(error_path)
            writer.writerow({key: row.get(key) for key in failure_fields})

    return {
        "summary": summary_path,
        "case_metrics": cases_path,
        "failures": failures_path,
    }
