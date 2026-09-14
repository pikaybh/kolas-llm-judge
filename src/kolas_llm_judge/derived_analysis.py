from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .identification import (
    HAZARD_IDENTIFICATION_DENOMINATOR,
    HAZARD_IDENTIFICATION_RULE,
    HAZARD_IDENTIFICATION_RULE_VERSION,
    HAZARD_SEMANTIC_IDENTIFICATION_DENOMINATOR,
    HAZARD_SEMANTIC_IDENTIFICATION_RULE,
    HAZARD_SEMANTIC_IDENTIFICATION_RULE_VERSION,
    identified_reference_ids,
)
from .io_utils import load_json, load_scenarios


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _reference_ids(matrix: list[dict[str, Any]]) -> set[str]:
    return {str(row["reference_id"]) for row in matrix}


def _any_by_reference(
    matrix: list[dict[str, Any]],
    predicate,
) -> set[str]:
    return {
        str(row["reference_id"])
        for row in matrix
        if predicate(row)
    }


def derive_identification_analysis(
    *,
    run_dir: Path,
    scenarios_path: Path,
) -> dict[str, Any]:
    scenarios = load_scenarios(scenarios_path)
    scenario_by_id = {scenario.case_id: scenario for scenario in scenarios}
    total_reference_count = sum(len(scenario.references) for scenario in scenarios)

    semantic_reference_ids: set[str] = set()
    identified_ids: set[str] = set()
    strict_many_to_one_ids: set[str] = set()
    same_only_ids: set[str] = set()
    accident_only_ids: set[str] = set()
    context_only_ids: set[str] = set()
    strict_1to1_ids: set[str] = set()
    judged_case_ids: set[str] = set()

    for judge_path in sorted((run_dir / "cases").glob("*/binary_judge.json")):
        case_id = judge_path.parent.name
        evaluation = load_json(judge_path).get("evaluation") or {}
        matrix = list(evaluation.get("match_matrix") or [])
        if not matrix:
            continue
        judged_case_ids.add(case_id)
        semantic_reference_ids.update(_reference_ids(matrix))
        identified_ids.update(identified_reference_ids(matrix))
        strict_many_to_one_ids.update(
            _any_by_reference(
                matrix,
                lambda row: bool(row.get("same_hazard_mechanism"))
                and bool(row.get("context_compatible")),
            )
        )
        same_only_ids.update(
            _any_by_reference(matrix, lambda row: bool(row.get("same_hazard_mechanism")))
        )
        accident_only_ids.update(
            _any_by_reference(matrix, lambda row: bool(row.get("accident_compatible")))
        )
        context_only_ids.update(
            _any_by_reference(matrix, lambda row: bool(row.get("context_compatible")))
        )
        strict_1to1_ids.update(
            str(row["reference_id"])
            for row in (evaluation.get("matches") or [])
        )

    exact_label_numerator = 0
    exact_label_denominator = 0
    parsed_case_ids: set[str] = set()
    for parsed_path in sorted((run_dir / "cases").glob("*/parsed.json")):
        case_id = parsed_path.parent.name
        scenario = scenario_by_id.get(case_id)
        if scenario is None:
            continue
        parsed = (load_json(parsed_path).get("parsed") or {})
        generated = parsed.get("risks") or []
        generated_accidents = [
            set(str(x) for x in (risk.get("accident_types") or []))
            for risk in generated
        ]
        parsed_case_ids.add(case_id)
        for reference in scenario.references:
            exact_label_denominator += 1
            reference_accidents = set(reference.accident_types)
            if any(reference_accidents & accidents for accidents in generated_accidents):
                exact_label_numerator += 1

    missing_by_failure_class: Counter[str] = Counter()
    missing_reference_count_by_failure_class: Counter[str] = Counter()
    for error_path in sorted((run_dir / "cases").glob("*/error.json")):
        if (error_path.parent / "result.json").exists():
            continue
        error = load_json(error_path)
        case_id = str(error.get("case_id") or error_path.parent.name)
        failure_class = str(error.get("failure_class") or "unknown")
        scenario = scenario_by_id.get(case_id)
        missing_by_failure_class[failure_class] += 1
        if scenario is not None:
            missing_reference_count_by_failure_class[failure_class] += len(
                scenario.references
            )

    semantic_denominator = len(semantic_reference_ids)
    manifest = load_json(run_dir / "manifest.json")
    verification_path = run_dir / "verification.json"
    verification = (
        load_json(verification_path)
        if verification_path.exists()
        else {}
    )
    seal_path = run_dir / "run_seal.json"
    seal = load_json(seal_path) if seal_path.exists() else {}
    source_seal_root = (
        verification.get("initial_seal_root_sha256")
        or seal.get("artifact_root_sha256")
    )

    return {
        "analysis_type": "derived-identification-analysis",
        "source_run_id": manifest.get("run_id") or run_dir.name,
        "source_run_dir": str(run_dir),
        "source_artifact_root_sha256": source_seal_root,
        "rule": {
            "primary": {
                "metric": "hazard_semantic_identification_recall",
                "version": HAZARD_SEMANTIC_IDENTIFICATION_RULE_VERSION,
                "expression": HAZARD_SEMANTIC_IDENTIFICATION_RULE,
                "denominator": HAZARD_SEMANTIC_IDENTIFICATION_DENOMINATOR,
            },
            "supplementary_kpi": {
                "metric": "hazard_identification_accuracy",
                "version": HAZARD_IDENTIFICATION_RULE_VERSION,
                "expression": HAZARD_IDENTIFICATION_RULE,
                "denominator": HAZARD_IDENTIFICATION_DENOMINATOR,
            },
            "notes": [
                "No new LLM calls are made; only persisted binary Judge decisions are reused.",
                "Strict 1:1 Reference Risk Coverage is preserved as a separate diagnostic.",
                "The source sealed run is read-only and is not modified by this analysis.",
            ],
        },
        "coverage": {
            "judged_cases": len(judged_case_ids),
            "parsed_cases": len(parsed_case_ids),
            "dataset_cases": len(scenarios),
            "semantic_evaluable_references": semantic_denominator,
            "dataset_references": total_reference_count,
            "references_without_semantic_judgment": (
                total_reference_count - semantic_denominator
            ),
            "failed_cases_by_class": dict(sorted(missing_by_failure_class.items())),
            "failed_references_by_class": dict(
                sorted(missing_reference_count_by_failure_class.items())
            ),
        },
        "metrics": {
            "hazard_semantic_identification_recall": _ratio(
                len(strict_many_to_one_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "hazard_identification_accuracy": _ratio(
                len(identified_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "strict_reference_risk_coverage_1to1": _ratio(
                len(strict_1to1_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "strict_semantic_coverage_many_to_one": _ratio(
                len(strict_many_to_one_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "same_hazard_mechanism_any": _ratio(
                len(same_only_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "accident_compatible_any": _ratio(
                len(accident_only_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "context_compatible_any": _ratio(
                len(context_only_ids & semantic_reference_ids),
                semantic_denominator,
            ),
            "exact_accident_label_intersection": _ratio(
                exact_label_numerator,
                exact_label_denominator,
            ),
            "end_to_end_hazard_identification_if_unjudged_are_failures": _ratio(
                len(identified_ids & semantic_reference_ids),
                total_reference_count,
            ),
        },
    }
