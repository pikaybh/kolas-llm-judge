from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from .automated_report import METRIC_NAMES, _case_metric
from .identification import semantically_identified_reference_ids
from .io_utils import load_json
from .seal import verify_run


def _metric_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None, "range": None}
    return {
        "count": len(values),
        "mean": fmean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
    }


def _identity(manifest: dict[str, Any]) -> dict[str, Any]:
    method = manifest.get("method_identity") or {}
    return {
        "selected_case_ids": manifest.get("selected_case_ids"),
        "dataset_sha256": ((manifest.get("dataset") or {}).get("sha256")),
        "method_identity": method,
        "sut_evaluation_identity": manifest.get("sut_evaluation_identity"),
    }


def _semantic_reference_state(run_dir: Path) -> dict[str, bool]:
    state: dict[str, bool] = {}
    for judge_path in sorted((run_dir / "cases").glob("*/binary_judge.json")):
        evaluation = (load_json(judge_path).get("evaluation") or {})
        matrix = list(evaluation.get("match_matrix") or [])
        reference_ids = {
            str(row.get("reference_id")) for row in matrix if row.get("reference_id")
        }
        identified = semantically_identified_reference_ids(matrix)
        for reference_id in reference_ids:
            state[reference_id] = reference_id in identified
    return state


def compare_sut_repeatability(
    run_dirs: list[Path],
    *,
    require_sealed: bool = True,
    require_same_identity: bool = True,
) -> dict[str, Any]:
    if len(run_dirs) < 2:
        raise ValueError("At least two runs are required for repeatability analysis")
    resolved = [path.resolve() for path in run_dirs]
    manifests = [load_json(path / "manifest.json") for path in resolved]
    identities = [_identity(m) for m in manifests]
    if require_same_identity and any(identity != identities[0] for identity in identities[1:]):
        raise ValueError("Runs do not share the same frozen evaluation/SUT identity")

    seal_results = [verify_run(path) for path in resolved]
    if require_sealed and not all(bool(row.get("ok")) for row in seal_results):
        raise ValueError("All repeatability runs must have valid SHA-256 seals")

    aggregate_values: dict[str, list[float]] = defaultdict(list)
    per_case_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    run_summaries: list[dict[str, Any]] = []
    reference_states: list[dict[str, bool]] = []

    for run_dir, manifest, seal in zip(resolved, manifests, seal_results):
        results = [load_json(p) for p in sorted((run_dir / "cases").glob("*/result.json"))]
        per_metric_micro: dict[str, list[int]] = {name: [0, 0] for name in METRIC_NAMES}
        for result in results:
            case_id = str(result.get("case_id"))
            for name in METRIC_NAMES:
                metric = _case_metric(run_dir, result, name)
                n, d = int(metric.get("numerator") or 0), int(metric.get("denominator") or 0)
                per_metric_micro[name][0] += n
                per_metric_micro[name][1] += d
                rate = metric.get("rate")
                if isinstance(rate, (int, float)):
                    per_case_values[case_id][name].append(float(rate))
        aggregate = {}
        for name, (n, d) in per_metric_micro.items():
            rate = n / d if d else None
            aggregate[name] = {"numerator": n, "denominator": d, "rate": rate}
            if rate is not None:
                aggregate_values[name].append(rate)
        run_summaries.append({
            "run_id": manifest.get("run_id") or run_dir.name,
            "seal_ok": bool(seal.get("ok")),
            "metrics": aggregate,
        })
        reference_states.append(_semantic_reference_state(run_dir))

    metric_stability = {name: _metric_stats(values) for name, values in sorted(aggregate_values.items())}
    case_stability: dict[str, Any] = {}
    for case_id, metrics in sorted(per_case_values.items()):
        case_stability[case_id] = {
            name: _metric_stats(values) for name, values in sorted(metrics.items())
        }

    common_references = set(reference_states[0])
    for state in reference_states[1:]:
        common_references &= set(state)
    per_reference = {}
    stable_count = 0
    for reference_id in sorted(common_references):
        values = [state[reference_id] for state in reference_states]
        detection_rate = sum(values) / len(values)
        stable = len(set(values)) == 1
        stable_count += int(stable)
        per_reference[reference_id] = {
            "detected_runs": sum(values),
            "total_runs": len(values),
            "detection_consistency": detection_rate,
            "stable_across_runs": stable,
        }

    return {
        "analysis_type": "sut-semantic-repeatability-v1",
        "run_count": len(resolved),
        "identity_verified": (not require_same_identity) or all(x == identities[0] for x in identities),
        "all_seals_verified": all(bool(row.get("ok")) for row in seal_results),
        "frozen_identity": identities[0],
        "runs": run_summaries,
        "aggregate_metric_stability": metric_stability,
        "per_case_metric_stability": case_stability,
        "semantic_reference_detection": {
            "common_reference_count": len(common_references),
            "stable_reference_count": stable_count,
            "stable_reference_rate": stable_count / len(common_references) if common_references else None,
            "per_reference": per_reference,
        },
    }
