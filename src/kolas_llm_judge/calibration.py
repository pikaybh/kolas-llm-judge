from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from sklearn.metrics import cohen_kappa_score

from .dataset import sha256_file
from .io_utils import atomic_write_json, load_json, load_scenarios
from .judge import JudgeConfig, LlmJudge
from .manifest import (
    capture_current_method_identity,
    method_identity_from_manifest,
    method_identity_matches,
)
from .models import (
    CaseJudgeResult,
    GeneratedRisk,
    ParsedRiskAssessment,
)


PAIR_DIMENSIONS: dict[str, dict[str, Any]] = {
    "semantic_match": {"max_score": 4, "pass_threshold": 3},
    "accident_type_correctness": {"max_score": 2, "pass_threshold": 2},
    "mitigation_appropriateness": {"max_score": 2, "pass_threshold": 2},
    "mitigation_specificity": {"max_score": 2, "pass_threshold": 2},
    "legal_basis_relevance": {"max_score": 2, "pass_threshold": 2},
}

GENERATED_DIMENSIONS = (
    "unsupported_claim",
    "critical_safety_error",
)


def _read_case_bundle(
    case_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = load_json(case_dir / "result.json")
    judge = load_json(case_dir / "judge.json")
    parsed = load_json(case_dir / "parsed.json")
    return result, judge, parsed


def _case_bundles(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_dir in sorted((run_dir / "cases").glob("case-*")):
        if not (case_dir / "result.json").exists():
            continue
        result, judge_payload, parsed_payload = _read_case_bundle(case_dir)
        judge = CaseJudgeResult.model_validate(judge_payload["result"])
        parsed = ParsedRiskAssessment.model_validate(
            parsed_payload["parsed"]
        )
        rows.append(
            {
                "_case_dir": case_dir,
                "_result": result,
                "_judge": judge,
                "_parsed": parsed,
                "_generated": {
                    item.generated_id: item for item in parsed.risks
                },
            }
        )
    return rows


def _normalize_label(value: str) -> str:
    return value.replace(" ", "").lower()


def _balanced_pair_sample(
    candidates: list[dict[str, Any]],
    *,
    sample_size: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    positives = [
        row for row in candidates if row["_proxy_positive"]
    ]
    negatives = [
        row for row in candidates if not row["_proxy_positive"]
    ]
    rng.shuffle(positives)
    rng.shuffle(negatives)

    target_positive = min(len(positives), sample_size // 2)
    target_negative = min(
        len(negatives),
        sample_size - target_positive,
    )
    selected = (
        positives[:target_positive]
        + negatives[:target_negative]
    )

    if len(selected) < sample_size:
        selected_keys = {
            (
                row["case_id"],
                row["reference_id"],
                row["generated_id"],
            )
            for row in selected
        }
        remainder = [
            row
            for row in candidates
            if (
                row["case_id"],
                row["reference_id"],
                row["generated_id"],
            )
            not in selected_keys
        ]
        rng.shuffle(remainder)
        selected.extend(
            remainder[: sample_size - len(selected)]
        )
    rng.shuffle(selected)
    return selected


def make_human_calibration_template(
    *,
    run_dir: Path,
    scenarios_path: Path,
    output_dir: Path,
    sample_size: int = 150,
    generated_sample_size: int | None = None,
    seed: int = 20260908,
) -> dict[str, Path]:
    scenario_map = {
        scenario.case_id: scenario
        for scenario in load_scenarios(scenarios_path)
    }
    pair_candidates: list[dict[str, Any]] = []
    generated_candidates: list[dict[str, Any]] = []

    for bundle in _case_bundles(run_dir):
        result = bundle["_result"]
        case_id = result["case_id"]
        scenario = scenario_map.get(case_id)
        if scenario is None:
            continue

        references = {
            item.reference_id: item
            for item in scenario.references
        }
        generated: dict[str, GeneratedRisk] = bundle["_generated"]
        judge: CaseJudgeResult = bundle["_judge"]

        for risk in generated.values():
            generated_candidates.append(
                {
                    "case_id": case_id,
                    "process": scenario.input.process,
                    "subprocess": scenario.input.subprocess or "",
                    "equipment": "; ".join(
                        scenario.input.equipment
                    ),
                    "materials": "; ".join(
                        scenario.input.materials
                    ),
                    "generated_id": risk.generated_id,
                    "generated_hazard": risk.hazard,
                    "generated_risk_cause": (
                        risk.risk_cause or ""
                    ),
                    "generated_accident_types": "; ".join(
                        risk.accident_types
                    ),
                    "generated_mitigation": (
                        risk.mitigation or ""
                    ),
                    "generated_legal_basis": (
                        risk.legal_basis or ""
                    ),
                }
            )

        for pair in judge.pair_evaluations:
            reference = references.get(pair.reference_id)
            risk = generated.get(pair.generated_id)
            if reference is None or risk is None:
                continue
            pair_candidates.append(
                {
                    "case_id": case_id,
                    "process": scenario.input.process,
                    "subprocess": scenario.input.subprocess or "",
                    "reference_id": reference.reference_id,
                    "reference_hazard": reference.hazard,
                    "reference_accident_types": "; ".join(
                        reference.accident_types
                    ),
                    "reference_mitigation": (
                        reference.mitigation or ""
                    ),
                    "reference_legal_basis": (
                        reference.legal_basis or ""
                    ),
                    "generated_id": risk.generated_id,
                    "generated_hazard": risk.hazard,
                    "generated_risk_cause": (
                        risk.risk_cause or ""
                    ),
                    "generated_accident_types": "; ".join(
                        risk.accident_types
                    ),
                    "generated_mitigation": (
                        risk.mitigation or ""
                    ),
                    "generated_legal_basis": (
                        risk.legal_basis or ""
                    ),
                    "_proxy_positive": bool(
                        {
                            _normalize_label(value)
                            for value in reference.accident_types
                        }
                        & {
                            _normalize_label(value)
                            for value in risk.accident_types
                        }
                    ),
                }
            )

    if not pair_candidates:
        raise RuntimeError(
            "No completed judged cases are available for calibration"
        )
    if not generated_candidates:
        raise RuntimeError(
            "No generated risks are available for calibration"
        )

    rng = random.Random(seed)
    selected_pairs = _balanced_pair_sample(
        pair_candidates,
        sample_size=min(sample_size, len(pair_candidates)),
        rng=rng,
    )

    generated_target = generated_sample_size or sample_size
    generated_target = min(
        generated_target,
        len(generated_candidates),
    )
    rng.shuffle(generated_candidates)
    selected_generated = generated_candidates[
        :generated_target
    ]

    output_dir.mkdir(parents=True, exist_ok=True)

    pair_fields = [
        "sample_id",
        "case_id",
        "process",
        "subprocess",
        "reference_id",
        "reference_hazard",
        "reference_accident_types",
        "reference_mitigation",
        "reference_legal_basis",
        "generated_id",
        "generated_hazard",
        "generated_risk_cause",
        "generated_accident_types",
        "generated_mitigation",
        "generated_legal_basis",
    ]
    for dimension in PAIR_DIMENSIONS:
        pair_fields.extend(
            [
                f"rater1_{dimension}",
                f"rater2_{dimension}",
                f"adjudicated_{dimension}",
            ]
        )
    pair_fields.append("notes")

    pairs_path = output_dir / "human_pairs.csv"
    with pairs_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=pair_fields,
        )
        writer.writeheader()
        for index, row in enumerate(
            selected_pairs,
            start=1,
        ):
            public = {
                key: row.get(key, "")
                for key in pair_fields
            }
            public["sample_id"] = f"P{index:04d}"
            writer.writerow(public)

    generated_fields = [
        "sample_id",
        "case_id",
        "process",
        "subprocess",
        "equipment",
        "materials",
        "generated_id",
        "generated_hazard",
        "generated_risk_cause",
        "generated_accident_types",
        "generated_mitigation",
        "generated_legal_basis",
    ]
    for dimension in GENERATED_DIMENSIONS:
        generated_fields.extend(
            [
                f"rater1_{dimension}",
                f"rater2_{dimension}",
                f"adjudicated_{dimension}",
            ]
        )
    generated_fields.append("notes")

    generated_path = output_dir / "human_generated.csv"
    with generated_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=generated_fields,
        )
        writer.writeheader()
        for index, row in enumerate(
            selected_generated,
            start=1,
        ):
            public = {
                key: row.get(key, "")
                for key in generated_fields
            }
            public["sample_id"] = f"G{index:04d}"
            writer.writerow(public)

    instructions_path = output_dir / "README.md"
    instructions_path.write_text(
        """# Human calibration labeling

두 평가자는 상대방의 점수와 Judge 점수를 보지 않고 독립적으로 평가합니다.

## human_pairs.csv

각 reference-generated pair에 대해 다음을 평가합니다.

- semantic_match: 0~4
  - 0: 무관/서로 다른 위험
  - 1: 작업 맥락은 비슷할 수 있으나 위험 메커니즘이 다름
  - 2: 부분 관련이나 핵심 원인/결과가 충분히 대응하지 않음
  - 3: 핵심 위험 메커니즘이 실질적으로 동일
  - 4: 위험 메커니즘과 작업 맥락이 사실상 동일
- accident_type_correctness: 0~2
- mitigation_appropriateness: 0~2
- mitigation_specificity: 0~2
- legal_basis_relevance: 0~2
  - generated_legal_basis가 비어 있으면 이 차원은 평가하지 않습니다.

0~2 차원은 0=부적합, 1=부분 적합, 2=적합입니다.

## human_generated.csv

reference와 무관하게 generated risk 자체를 평가합니다.

- unsupported_claim: 0/1
  - 1 = 입력 작업 맥락 또는 합리적 건설안전 지식으로 뒷받침되지 않음
- critical_safety_error: 0/1
  - 1 = 잘못된 조치가 실행되면 중대한 위해를 유발하거나 필수 통제를 반대로 안내

두 평가자의 값이 다르면 협의 후 adjudicated_* 열에 최종값을 입력합니다.
두 값이 같으면 adjudicated_*는 비워도 동일값을 consensus로 사용합니다.
Judge 예측은 두 CSV에 포함되지 않습니다.
""",
        encoding="utf-8",
    )

    metadata_path = output_dir / "sample_manifest.json"
    atomic_write_json(
        metadata_path,
        {
            "pair_sample_size_requested": sample_size,
            "pair_sample_size_actual": len(selected_pairs),
            "generated_sample_size_requested": (
                generated_sample_size or sample_size
            ),
            "generated_sample_size_actual": (
                len(selected_generated)
            ),
            "seed": seed,
            "pair_sampling": (
                "balanced by deterministic accident-label-overlap "
                "proxy vs non-overlap; Judge scores not used"
            ),
            "generated_sampling": (
                "uniform deterministic shuffle by fixed seed; "
                "Judge scores not used"
            ),
            "source_run": str(run_dir),
            "source_scenarios": str(scenarios_path),
            "judge_scores_exposed_to_humans": False,
        },
    )
    return {
        "pairs": pairs_path,
        "generated": generated_path,
        "instructions": instructions_path,
        "manifest": metadata_path,
    }


def _parse_score(
    value: str,
    *,
    max_score: int,
) -> int | None:
    value = value.strip()
    if value == "":
        return None
    score = int(value)
    if not 0 <= score <= max_score:
        raise ValueError(
            f"Score must be 0..{max_score}, got {score}"
        )
    return score


def _parse_bool_score(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized == "":
        return None
    if normalized in {"1", "true", "yes", "y"}:
        return 1
    if normalized in {"0", "false", "no", "n"}:
        return 0
    raise ValueError(
        f"Boolean calibration value must be 0/1 or true/false, got {value!r}"
    )


def _safe_kappa(
    a: list[int],
    b: list[int],
) -> float | None:
    if not a or len(a) != len(b):
        return None
    if len(set(a) | set(b)) < 2:
        return 1.0 if a == b else None
    value = float(cohen_kappa_score(a, b))
    return None if value != value else value


def _agreement(
    a: list[int],
    b: list[int],
) -> float | None:
    if not a or len(a) != len(b):
        return None
    return (
        sum(x == y for x, y in zip(a, b))
        / len(a)
    )


def _resolve_human_target(
    *,
    rater1: int | None,
    rater2: int | None,
    adjudicated: int | None,
) -> tuple[int | None, bool]:
    if adjudicated is not None:
        return adjudicated, True
    if (
        rater1 is not None
        and rater2 is not None
        and rater1 == rater2
    ):
        return rater1, True
    return None, False


def _judge_maps(
    run_dir: Path,
) -> tuple[
    dict[tuple[str, str, str], dict[str, int]],
    dict[tuple[str, str], dict[str, bool]],
]:
    pairs: dict[
        tuple[str, str, str],
        dict[str, int],
    ] = {}
    generated: dict[
        tuple[str, str],
        dict[str, bool],
    ] = {}

    for case_dir in sorted(
        (run_dir / "cases").glob("case-*")
    ):
        judge_path = case_dir / "judge.json"
        if not judge_path.exists():
            continue
        case_id = case_dir.name
        judge = CaseJudgeResult.model_validate(
            load_json(judge_path)["result"]
        )
        for pair in judge.pair_evaluations:
            pairs[
                (
                    case_id,
                    pair.reference_id,
                    pair.generated_id,
                )
            ] = {
                dimension: int(
                    getattr(pair, dimension)
                )
                for dimension in PAIR_DIMENSIONS
            }
        for item in judge.generated_evaluations:
            generated[
                (case_id, item.generated_id)
            ] = {
                "unsupported_claim": bool(
                    item.unsupported_claim
                ),
                "critical_safety_error": bool(
                    item.critical_safety_error
                ),
            }
    return pairs, generated


def _score_pair_dimension(
    *,
    rows: list[dict[str, str]],
    judge_map: dict[
        tuple[str, str, str],
        dict[str, int],
    ],
    dimension: str,
) -> dict[str, Any]:
    cfg = PAIR_DIMENSIONS[dimension]
    max_score = int(cfg["max_score"])
    pass_threshold = int(cfg["pass_threshold"])

    r1_binary: list[int] = []
    r2_binary: list[int] = []
    human_binary: list[int] = []
    judge_binary: list[int] = []
    human_exact: list[int] = []
    judge_exact: list[int] = []
    applicable = 0
    resolved = 0
    missing_judge = 0

    for row in rows:
        if (
            dimension == "legal_basis_relevance"
            and not row.get(
                "generated_legal_basis",
                "",
            ).strip()
        ):
            continue
        applicable += 1

        r1 = _parse_score(
            row.get(f"rater1_{dimension}", ""),
            max_score=max_score,
        )
        r2 = _parse_score(
            row.get(f"rater2_{dimension}", ""),
            max_score=max_score,
        )
        adj = _parse_score(
            row.get(
                f"adjudicated_{dimension}",
                "",
            ),
            max_score=max_score,
        )

        if r1 is not None and r2 is not None:
            r1_binary.append(
                int(r1 >= pass_threshold)
            )
            r2_binary.append(
                int(r2 >= pass_threshold)
            )

        target, is_resolved = _resolve_human_target(
            rater1=r1,
            rater2=r2,
            adjudicated=adj,
        )
        if not is_resolved or target is None:
            continue
        resolved += 1

        key = (
            row["case_id"],
            row["reference_id"],
            row["generated_id"],
        )
        judge_values = judge_map.get(key)
        if judge_values is None:
            missing_judge += 1
            continue
        judge_score = int(
            judge_values[dimension]
        )
        human_exact.append(target)
        judge_exact.append(judge_score)
        human_binary.append(
            int(target >= pass_threshold)
        )
        judge_binary.append(
            int(judge_score >= pass_threshold)
        )

    return {
        "applicable_rows": applicable,
        "resolved_rows": resolved,
        "label_completion": (
            resolved / applicable
            if applicable
            else None
        ),
        "missing_judge_rows": missing_judge,
        "human_human_binary_agreement": (
            _agreement(r1_binary, r2_binary)
        ),
        "human_human_binary_kappa": (
            _safe_kappa(r1_binary, r2_binary)
        ),
        "judge_human_binary_agreement": (
            _agreement(
                human_binary,
                judge_binary,
            )
        ),
        "judge_human_binary_kappa": (
            _safe_kappa(
                human_binary,
                judge_binary,
            )
        ),
        "judge_human_exact_score_agreement": (
            _agreement(
                human_exact,
                judge_exact,
            )
        ),
        "sample_count": len(human_binary),
    }


def _score_generated_dimension(
    *,
    rows: list[dict[str, str]],
    judge_map: dict[
        tuple[str, str],
        dict[str, bool],
    ],
    dimension: str,
) -> dict[str, Any]:
    r1_values: list[int] = []
    r2_values: list[int] = []
    human_values: list[int] = []
    judge_values_out: list[int] = []
    resolved = 0
    missing_judge = 0

    for row in rows:
        r1 = _parse_bool_score(
            row.get(f"rater1_{dimension}", "")
        )
        r2 = _parse_bool_score(
            row.get(f"rater2_{dimension}", "")
        )
        adj = _parse_bool_score(
            row.get(
                f"adjudicated_{dimension}",
                "",
            )
        )
        if r1 is not None and r2 is not None:
            r1_values.append(r1)
            r2_values.append(r2)

        target, is_resolved = _resolve_human_target(
            rater1=r1,
            rater2=r2,
            adjudicated=adj,
        )
        if not is_resolved or target is None:
            continue
        resolved += 1

        judge_values = judge_map.get(
            (
                row["case_id"],
                row["generated_id"],
            )
        )
        if judge_values is None:
            missing_judge += 1
            continue
        human_values.append(target)
        judge_values_out.append(
            int(bool(judge_values[dimension]))
        )

    applicable = len(rows)
    return {
        "applicable_rows": applicable,
        "resolved_rows": resolved,
        "label_completion": (
            resolved / applicable
            if applicable
            else None
        ),
        "missing_judge_rows": missing_judge,
        "human_human_agreement": (
            _agreement(r1_values, r2_values)
        ),
        "human_human_kappa": (
            _safe_kappa(r1_values, r2_values)
        ),
        "judge_human_agreement": (
            _agreement(
                human_values,
                judge_values_out,
            )
        ),
        "judge_human_kappa": (
            _safe_kappa(
                human_values,
                judge_values_out,
            )
        ),
        "sample_count": len(human_values),
        "human_positive_rate": (
            sum(human_values)
            / len(human_values)
            if human_values
            else None
        ),
        "judge_positive_rate": (
            sum(judge_values_out)
            / len(judge_values_out)
            if judge_values_out
            else None
        ),
    }


def _structured_completion(
    run_dir: Path,
) -> dict[str, Any]:
    pair_completed = 0
    pair_expected = 0
    generated_completed = 0
    generated_expected = 0

    for case_dir in sorted(
        (run_dir / "cases").glob("case-*")
    ):
        parsed_path = case_dir / "parsed.json"
        judge_path = case_dir / "judge.json"
        result_path = case_dir / "result.json"
        if not (
            parsed_path.exists()
            and judge_path.exists()
            and result_path.exists()
        ):
            continue

        parsed = ParsedRiskAssessment.model_validate(
            load_json(parsed_path)["parsed"]
        )
        judge = CaseJudgeResult.model_validate(
            load_json(judge_path)["result"]
        )
        reference_count = int(
            load_json(result_path)["reference_count"]
        )
        pair_expected += (
            reference_count * len(parsed.risks)
        )
        pair_completed += len(
            judge.pair_evaluations
        )
        generated_expected += len(parsed.risks)
        generated_completed += len(
            judge.generated_evaluations
        )

    pair_rate = (
        pair_completed / pair_expected
        if pair_expected
        else None
    )
    generated_rate = (
        generated_completed / generated_expected
        if generated_expected
        else None
    )
    rates = [
        value
        for value in [pair_rate, generated_rate]
        if value is not None
    ]
    return {
        "pair": {
            "completed": pair_completed,
            "expected": pair_expected,
            "rate": pair_rate,
        },
        "generated": {
            "completed": generated_completed,
            "expected": generated_expected,
            "rate": generated_rate,
        },
        "minimum_rate": (
            min(rates) if rates else None
        ),
    }


def score_human_calibration(
    *,
    run_dir: Path,
    labeled_pairs_csv: Path,
    labeled_generated_csv: Path | None = None,
    repeatability_summary: Path | None = None,
    semantic_agreement_min: float = 0.90,
    semantic_kappa_min: float = 0.70,
    dimension_agreement_min: float = 0.85,
    dimension_kappa_min: float = 0.60,
    generated_agreement_min: float = 0.90,
    repeatability_min: float = 0.95,
    structured_completion_min: float = 0.99,
    human_label_completion_min: float = 1.0,
    min_pair_samples: int = 30,
    min_generated_samples: int = 30,
) -> dict[str, Any]:
    if labeled_generated_csv is None:
        labeled_generated_csv = (
            labeled_pairs_csv.parent
            / "human_generated.csv"
        )
    if not labeled_generated_csv.exists():
        raise FileNotFoundError(
            "Generated-risk human calibration file is missing: "
            f"{labeled_generated_csv}"
        )

    with labeled_pairs_csv.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        pair_rows = list(csv.DictReader(f))
    with labeled_generated_csv.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        generated_rows = list(csv.DictReader(f))

    pair_judge_map, generated_judge_map = (
        _judge_maps(run_dir)
    )
    pair_dimensions = {
        dimension: _score_pair_dimension(
            rows=pair_rows,
            judge_map=pair_judge_map,
            dimension=dimension,
        )
        for dimension in PAIR_DIMENSIONS
    }
    generated_dimensions = {
        dimension: _score_generated_dimension(
            rows=generated_rows,
            judge_map=generated_judge_map,
            dimension=dimension,
        )
        for dimension in GENERATED_DIMENSIONS
    }

    structured = _structured_completion(run_dir)

    source_manifest_path = run_dir / "manifest.json"
    frozen_method: dict[str, Any] | None = None
    if source_manifest_path.exists():
        source_manifest = load_json(source_manifest_path)
        source_identity = method_identity_from_manifest(source_manifest)
        if source_identity is not None:
            source_git = source_manifest.get("git")
            frozen_method = {
                "source_run_id": source_manifest.get("run_id"),
                "source_run_manifest_sha256": sha256_file(source_manifest_path),
                "source_evaluation_git_head": (
                    source_git.get("head")
                    if isinstance(source_git, dict)
                    else None
                ),
                "source_evaluation_git_clean": (
                    not bool(source_git.get("dirty"))
                    if isinstance(source_git, dict)
                    else False
                ),
                "method_identity": source_identity,
            }

    repeatability_data: dict[str, Any] = {}
    if (
        repeatability_summary
        and repeatability_summary.exists()
    ):
        repeatability_data = load_json(
            repeatability_summary
        )
    repeatability = repeatability_data.get(
        "repeatability"
    )
    min_dimension_repeatability = (
        repeatability_data.get(
            "minimum_dimension_repeatability"
        )
    )

    checks: dict[str, dict[str, Any]] = {}
    checks["calibration_run_manifest_binding"] = {
        "value": bool(frozen_method),
        "minimum": True,
        "pass": bool(frozen_method),
    }
    source_eval_clean = bool(
        frozen_method
        and frozen_method.get("source_evaluation_git_head")
        and frozen_method.get("source_evaluation_git_clean") is True
    )
    checks["calibration_source_evaluator_committed_clean"] = {
        "value": source_eval_clean,
        "minimum": True,
        "pass": source_eval_clean,
    }

    semantic = pair_dimensions["semantic_match"]
    checks["semantic_agreement"] = {
        "value": semantic[
            "judge_human_binary_agreement"
        ],
        "minimum": semantic_agreement_min,
        "pass": (
            semantic[
                "judge_human_binary_agreement"
            ]
            is not None
            and semantic[
                "judge_human_binary_agreement"
            ]
            >= semantic_agreement_min
        ),
    }
    checks["semantic_kappa"] = {
        "value": semantic[
            "judge_human_binary_kappa"
        ],
        "minimum": semantic_kappa_min,
        "pass": (
            semantic[
                "judge_human_binary_kappa"
            ]
            is not None
            and semantic[
                "judge_human_binary_kappa"
            ]
            >= semantic_kappa_min
        ),
    }

    for dimension in (
        "accident_type_correctness",
        "mitigation_appropriateness",
        "mitigation_specificity",
        "legal_basis_relevance",
    ):
        score = pair_dimensions[dimension]
        checks[f"{dimension}_agreement"] = {
            "value": score[
                "judge_human_binary_agreement"
            ],
            "minimum": dimension_agreement_min,
            "pass": (
                score[
                    "judge_human_binary_agreement"
                ]
                is not None
                and score[
                    "judge_human_binary_agreement"
                ]
                >= dimension_agreement_min
            ),
        }
        checks[f"{dimension}_kappa"] = {
            "value": score[
                "judge_human_binary_kappa"
            ],
            "minimum": dimension_kappa_min,
            "pass": (
                score[
                    "judge_human_binary_kappa"
                ]
                is not None
                and score[
                    "judge_human_binary_kappa"
                ]
                >= dimension_kappa_min
            ),
        }

    for dimension in GENERATED_DIMENSIONS:
        score = generated_dimensions[dimension]
        checks[f"{dimension}_agreement"] = {
            "value": score[
                "judge_human_agreement"
            ],
            "minimum": generated_agreement_min,
            "pass": (
                score["judge_human_agreement"]
                is not None
                and score[
                    "judge_human_agreement"
                ]
                >= generated_agreement_min
            ),
            "note": (
                "Kappa is reported descriptively but not "
                "used as a hard gate because rare safety "
                "events can make kappa prevalence-sensitive."
            ),
        }

    pair_completion_values = [
        score["label_completion"]
        for score in pair_dimensions.values()
        if score["applicable_rows"] > 0
    ]
    generated_completion_values = [
        score["label_completion"]
        for score in generated_dimensions.values()
        if score["applicable_rows"] > 0
    ]
    all_completion_values = [
        value
        for value in (
            pair_completion_values
            + generated_completion_values
        )
        if value is not None
    ]
    minimum_human_completion = (
        min(all_completion_values)
        if all_completion_values
        else None
    )
    checks["human_label_completion"] = {
        "value": minimum_human_completion,
        "minimum": human_label_completion_min,
        "pass": (
            minimum_human_completion is not None
            and minimum_human_completion
            >= human_label_completion_min
        ),
    }

    pair_sample_min = min(
        (
            score["sample_count"]
            for score in pair_dimensions.values()
            if score["applicable_rows"] > 0
        ),
        default=0,
    )
    generated_sample_min = min(
        (
            score["sample_count"]
            for score in generated_dimensions.values()
            if score["applicable_rows"] > 0
        ),
        default=0,
    )
    checks["pair_sample_size"] = {
        "value": pair_sample_min,
        "minimum": min_pair_samples,
        "pass": pair_sample_min >= min_pair_samples,
    }
    checks["generated_sample_size"] = {
        "value": generated_sample_min,
        "minimum": min_generated_samples,
        "pass": (
            generated_sample_min
            >= min_generated_samples
        ),
    }

    structured_rate = structured["minimum_rate"]
    checks["structured_completion"] = {
        "value": structured_rate,
        "minimum": structured_completion_min,
        "pass": (
            structured_rate is not None
            and structured_rate
            >= structured_completion_min
        ),
    }
    checks["repeatability"] = {
        "value": repeatability,
        "minimum": repeatability_min,
        "pass": (
            repeatability is not None
            and repeatability
            >= repeatability_min
        ),
    }
    if min_dimension_repeatability is not None:
        checks[
            "minimum_dimension_repeatability"
        ] = {
            "value": min_dimension_repeatability,
            "minimum": repeatability_min,
            "pass": (
                min_dimension_repeatability
                >= repeatability_min
            ),
        }

    return {
        "pair_rows": len(pair_rows),
        "generated_rows": len(generated_rows),
        "pair_dimensions": pair_dimensions,
        "generated_dimensions": generated_dimensions,
        "structured_completion": structured,
        "repeatability": repeatability_data,
        "frozen_method": frozen_method,
        "checks": checks,
        "gate_pass": all(
            check["pass"]
            for check in checks.values()
        ),
    }


async def run_judge_repeatability(
    *,
    run_dir: Path,
    scenarios_path: Path,
    output_dir: Path,
    project_root: Path | None = None,
    repeats: int = 3,
    max_cases: int = 20,
) -> dict[str, Any]:
    scenarios = {
        scenario.case_id: scenario
        for scenario in load_scenarios(
            scenarios_path
        )
    }
    available = [
        path
        for path in sorted(
            (run_dir / "cases").glob("case-*")
        )
        if (path / "parsed.json").exists()
    ][:max_cases]
    if not available:
        raise RuntimeError(
            "No parsed completed cases are available"
        )

    source_manifest_path = run_dir / "manifest.json"
    if not source_manifest_path.exists():
        raise RuntimeError(
            "Repeatability requires the source run manifest."
        )
    source_manifest = load_json(source_manifest_path)
    frozen_identity = method_identity_from_manifest(source_manifest)
    if frozen_identity is None:
        raise RuntimeError(
            "Source run manifest has no method identity."
        )
    root = project_root
    if root is None:
        if run_dir.parent.name == "runs":
            root = run_dir.parent.parent
        else:
            raise RuntimeError(
                "project_root is required to verify Judge repeatability identity."
            )
    judge_config = JudgeConfig.from_env()
    current_identity = capture_current_method_identity(
        project_root=root,
        scenarios_path=scenarios_path,
        judge=judge_config,
    )
    if not method_identity_matches(
        frozen_identity,
        current_identity,
    ):
        raise RuntimeError(
            "Current Judge/evaluation method differs from the pilot run; "
            "repeatability must use the frozen method identity."
        )

    judge = LlmJudge(judge_config)
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions: dict[
        str,
        dict[str, list[int]],
    ] = {
        dimension: defaultdict(list)
        for dimension in (
            *PAIR_DIMENSIONS.keys(),
            *GENERATED_DIMENSIONS,
        )
    }

    for case_dir in available:
        scenario = scenarios[case_dir.name]
        parsed = ParsedRiskAssessment.model_validate(
            load_json(
                case_dir / "parsed.json"
            )["parsed"]
        )
        case_output = output_dir / case_dir.name
        case_output.mkdir(
            parents=True,
            exist_ok=True,
        )
        for repeat_index in range(
            1,
            repeats + 1,
        ):
            path = (
                case_output
                / f"repeat-{repeat_index}.json"
            )
            if path.exists():
                result = (
                    CaseJudgeResult.model_validate(
                        load_json(path)["result"]
                    )
                )
            else:
                record = await judge.evaluate_case(
                    scenario,
                    parsed.risks,
                )
                result = record.result
                atomic_write_json(
                    path,
                    {
                        "result": (
                            result.model_dump(
                                mode="json"
                            )
                        ),
                        "response_id": (
                            record.response_id
                        ),
                        "response_model": (
                            record.response_model
                        ),
                        "usage": record.usage,
                        "calls": record.calls,
                    },
                )

            for pair in result.pair_evaluations:
                key = (
                    f"{case_dir.name}:"
                    f"{pair.reference_id}:"
                    f"{pair.generated_id}"
                )
                for dimension, cfg in (
                    PAIR_DIMENSIONS.items()
                ):
                    score = int(
                        getattr(pair, dimension)
                    )
                    decisions[dimension][
                        key
                    ].append(
                        int(
                            score
                            >= int(
                                cfg[
                                    "pass_threshold"
                                ]
                            )
                        )
                    )

            for item in (
                result.generated_evaluations
            ):
                key = (
                    f"{case_dir.name}:"
                    f"{item.generated_id}"
                )
                for dimension in (
                    GENERATED_DIMENSIONS
                ):
                    decisions[dimension][
                        key
                    ].append(
                        int(
                            bool(
                                getattr(
                                    item,
                                    dimension,
                                )
                            )
                        )
                    )

    by_dimension: dict[str, Any] = {}
    all_complete: list[list[int]] = []

    for dimension, dimension_values in (
        decisions.items()
    ):
        complete = [
            values
            for values in dimension_values.values()
            if len(values) == repeats
        ]
        stable = sum(
            len(set(values)) == 1
            for values in complete
        )
        rate = (
            stable / len(complete)
            if complete
            else None
        )
        by_dimension[dimension] = {
            "decision_count": len(complete),
            "stable_decision_count": stable,
            "repeatability": rate,
        }
        all_complete.extend(complete)

    all_stable = sum(
        len(set(values)) == 1
        for values in all_complete
    )
    overall = (
        all_stable / len(all_complete)
        if all_complete
        else None
    )
    dimension_rates = [
        row["repeatability"]
        for row in by_dimension.values()
        if row["repeatability"] is not None
    ]

    summary = {
        "repeats": repeats,
        "case_count": len(available),
        "decision_count": len(all_complete),
        "stable_decision_count": all_stable,
        "repeatability": overall,
        "minimum_dimension_repeatability": (
            min(dimension_rates)
            if dimension_rates
            else None
        ),
        "by_dimension": by_dimension,
    }
    atomic_write_json(
        output_dir / "summary.json",
        summary,
    )
    return summary
