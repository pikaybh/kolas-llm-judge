from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from sklearn.metrics import cohen_kappa_score

from .dataset import sha256_file
from .io_utils import atomic_write_json, load_json, load_scenarios
from .models import ParsedRiskAssessment
from .seal import verify_run

MATCH_DIMENSIONS = (
    "same_hazard_mechanism",
    "context_compatible",
    "accident_compatible",
)
QUALITY_DIMENSIONS = (
    "mitigation_addresses_hazard",
    "mitigation_actionable",
    "mitigation_specific",
    "legal_basis_relevant",
    "unsafe_advice",
)
SAFETY_DIMENSIONS = ("critical_safety_error",)
PRIMARY_COMPOSITE = "semantic_identification_match"


def _parse_bool(value: str) -> int | None:
    normalized = str(value or "").strip().lower()
    if normalized == "":
        return None
    if normalized in {"1", "true", "yes", "y"}:
        return 1
    if normalized in {"0", "false", "no", "n"}:
        return 0
    raise ValueError(f"Boolean calibration value must be 0/1 or true/false, got {value!r}")


def _resolve(r1: int | None, r2: int | None, adjudicated: int | None) -> tuple[int | None, bool]:
    if adjudicated is not None:
        return adjudicated, True
    if r1 is not None and r2 is not None and r1 == r2:
        return r1, True
    return None, False


def _agreement(a: list[int], b: list[int]) -> float | None:
    if not a or len(a) != len(b):
        return None
    return sum(x == y for x, y in zip(a, b)) / len(a)


def _kappa(a: list[int], b: list[int]) -> float | None:
    if not a or len(a) != len(b):
        return None
    if len(set(a) | set(b)) < 2:
        return 1.0 if a == b else None
    value = float(cohen_kappa_score(a, b))
    return None if value != value else value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _sample_identity_sha256(
    rows: list[dict[str, Any]],
    fields: list[str],
) -> str:
    payload = [
        {field: str(row.get(field, "")) for field in fields}
        for row in rows
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _csv_identity_sha256(path: Path, fields: list[str]) -> str:
    return _sample_identity_sha256(_read_csv(path), fields)


def _label_fields(dimensions: tuple[str, ...]) -> list[str]:
    fields: list[str] = []
    for dimension in dimensions:
        fields.extend(
            [
                f"rater1_{dimension}",
                f"rater2_{dimension}",
                f"adjudicated_{dimension}",
            ]
        )
    return fields


def _accident_overlap(reference: list[str], generated: list[str]) -> bool:
    def norm(values: list[str]) -> set[str]:
        return {str(value).replace(" ", "").casefold() for value in values if str(value).strip()}
    return bool(norm(reference) & norm(generated))


def _balanced_proxy_sample(
    rows: list[dict[str, Any]], *, sample_size: int, rng: random.Random
) -> list[dict[str, Any]]:
    positive = [row for row in rows if row.get("_proxy_positive")]
    negative = [row for row in rows if not row.get("_proxy_positive")]
    rng.shuffle(positive)
    rng.shuffle(negative)
    target_pos = min(len(positive), sample_size // 2)
    target_neg = min(len(negative), sample_size - target_pos)
    selected = positive[:target_pos] + negative[:target_neg]
    if len(selected) < sample_size:
        selected_ids = {row["_key"] for row in selected}
        remainder = [row for row in rows if row["_key"] not in selected_ids]
        rng.shuffle(remainder)
        selected.extend(remainder[: sample_size - len(selected)])
    rng.shuffle(selected)
    return selected


def _official_case_data(run_dir: Path, scenarios_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scenario_map = {scenario.case_id: scenario for scenario in load_scenarios(scenarios_path)}
    match_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    safety_rows: list[dict[str, Any]] = []

    for case_dir in sorted((run_dir / "cases").glob("case-*")):
        parsed_path = case_dir / "parsed.json"
        judge_path = case_dir / "binary_judge.json"
        result_path = case_dir / "result.json"
        if not (parsed_path.exists() and judge_path.exists() and result_path.exists()):
            continue
        case_id = case_dir.name
        scenario = scenario_map.get(case_id)
        if scenario is None:
            continue
        parsed = ParsedRiskAssessment.model_validate(load_json(parsed_path)["parsed"])
        generated = {risk.generated_id: risk for risk in parsed.risks}
        references = {reference.reference_id: reference for reference in scenario.references}
        evaluation = load_json(judge_path).get("evaluation") or {}

        for risk in parsed.risks:
            safety_rows.append(
                {
                    "_key": (case_id, risk.generated_id),
                    "case_id": case_id,
                    "process": scenario.input.process,
                    "subprocess": scenario.input.subprocess or "",
                    "equipment": "; ".join(scenario.input.equipment),
                    "materials": "; ".join(scenario.input.materials),
                    "generated_id": risk.generated_id,
                    "generated_hazard": risk.hazard,
                    "generated_risk_cause": risk.risk_cause or "",
                    "generated_accident_types": "; ".join(risk.accident_types),
                    "generated_mitigation": risk.mitigation or "",
                    "generated_legal_basis": risk.legal_basis or "",
                }
            )

        for decision in evaluation.get("match_matrix") or []:
            reference = references.get(str(decision.get("reference_id")))
            risk = generated.get(str(decision.get("generated_id")))
            if reference is None or risk is None:
                continue
            common = {
                "_key": (case_id, reference.reference_id, risk.generated_id),
                "case_id": case_id,
                "process": scenario.input.process,
                "subprocess": scenario.input.subprocess or "",
                "reference_id": reference.reference_id,
                "reference_hazard": reference.hazard,
                "reference_accident_types": "; ".join(reference.accident_types),
                "reference_mitigation": reference.mitigation or "",
                "reference_legal_basis": reference.legal_basis or "",
                "generated_id": risk.generated_id,
                "generated_hazard": risk.hazard,
                "generated_risk_cause": risk.risk_cause or "",
                "generated_accident_types": "; ".join(risk.accident_types),
                "generated_mitigation": risk.mitigation or "",
                "generated_legal_basis": risk.legal_basis or "",
            }
            match_rows.append(
                {
                    **common,
                    "_proxy_positive": _accident_overlap(reference.accident_types, risk.accident_types),
                }
            )

        for decision in evaluation.get("quality") or []:
            reference = references.get(str(decision.get("reference_id")))
            risk = generated.get(str(decision.get("generated_id")))
            if reference is None or risk is None:
                continue
            quality_rows.append(
                {
                    "_key": (case_id, reference.reference_id, risk.generated_id),
                    "case_id": case_id,
                    "process": scenario.input.process,
                    "subprocess": scenario.input.subprocess or "",
                    "reference_id": reference.reference_id,
                    "reference_hazard": reference.hazard,
                    "reference_mitigation": reference.mitigation or "",
                    "reference_legal_basis": reference.legal_basis or "",
                    "generated_id": risk.generated_id,
                    "generated_hazard": risk.hazard,
                    "generated_risk_cause": risk.risk_cause or "",
                    "generated_mitigation": risk.mitigation or "",
                    "generated_legal_basis": risk.legal_basis or "",
                }
            )

    if not match_rows:
        raise RuntimeError("No official binary match-matrix rows are available for calibration")
    if not quality_rows:
        raise RuntimeError("No official binary quality rows are available for calibration")
    if not safety_rows:
        raise RuntimeError("No generated risks are available for binary safety calibration")
    return match_rows, quality_rows, safety_rows


def make_binary_human_calibration_template(
    *,
    run_dir: Path,
    scenarios_path: Path,
    output_dir: Path,
    match_sample_size: int = 150,
    quality_sample_size: int = 100,
    safety_sample_size: int = 100,
    seed: int = 20260914,
    require_sealed: bool = True,
) -> dict[str, Path]:
    source_verification = verify_run(run_dir)
    if require_sealed and not source_verification.get("ok"):
        raise RuntimeError(
            "Binary human calibration requires an intact sealed source run: "
            f"{source_verification}"
        )
    matches, quality, safety = _official_case_data(run_dir, scenarios_path)
    rng = random.Random(seed)
    selected_matches = _balanced_proxy_sample(
        matches, sample_size=min(match_sample_size, len(matches)), rng=rng
    )
    rng.shuffle(quality)
    selected_quality = quality[: min(quality_sample_size, len(quality))]
    rng.shuffle(safety)
    selected_safety = safety[: min(safety_sample_size, len(safety))]

    output_dir.mkdir(parents=True, exist_ok=True)
    match_identity_fields = [
        "sample_id", "case_id", "process", "subprocess",
        "reference_id", "reference_hazard", "reference_accident_types",
        "generated_id", "generated_hazard", "generated_risk_cause",
        "generated_accident_types",
    ]
    quality_identity_fields = [
        "sample_id", "case_id", "process", "subprocess",
        "reference_id", "reference_hazard", "reference_mitigation", "reference_legal_basis",
        "generated_id", "generated_hazard", "generated_risk_cause",
        "generated_mitigation", "generated_legal_basis",
    ]
    safety_identity_fields = [
        "sample_id", "case_id", "process", "subprocess", "equipment", "materials",
        "generated_id", "generated_hazard", "generated_risk_cause",
        "generated_accident_types", "generated_mitigation", "generated_legal_basis",
    ]
    match_fields = [*match_identity_fields, *_label_fields(MATCH_DIMENSIONS), "notes"]
    quality_fields = [*quality_identity_fields, *_label_fields(QUALITY_DIMENSIONS), "notes"]
    safety_fields = [*safety_identity_fields, *_label_fields(SAFETY_DIMENSIONS), "notes"]

    match_path = output_dir / "human_binary_match.csv"
    quality_path = output_dir / "human_binary_quality.csv"
    safety_path = output_dir / "human_binary_safety.csv"
    match_public = [{**row, "sample_id": f"M{i:04d}"} for i, row in enumerate(selected_matches, 1)]
    quality_public = [{**row, "sample_id": f"Q{i:04d}"} for i, row in enumerate(selected_quality, 1)]
    safety_public = [{**row, "sample_id": f"S{i:04d}"} for i, row in enumerate(selected_safety, 1)]
    _write_csv(match_path, match_fields, match_public)
    _write_csv(quality_path, quality_fields, quality_public)
    _write_csv(safety_path, safety_fields, safety_public)

    instructions = output_dir / "README_BINARY.md"
    instructions.write_text(
        """# KOLAS binary human calibration

두 안전전문가는 상대방의 판정과 LLM Judge 판정을 보지 않고 독립적으로 0/1을 입력합니다.
불일치 시 협의 후 `adjudicated_*` 열을 확정합니다. Judge 결과는 CSV에 노출되지 않습니다.

## Match

- `same_hazard_mechanism`: 핵심 위험 발생 메커니즘이 실질적으로 동일
- `context_compatible`: 작업·설비·노출 맥락이 동일하거나 양립 가능
- `accident_compatible`: 사고유형 또는 피해 메커니즘이 직접 호환
- KOLAS primary composite: `same_hazard_mechanism AND context_compatible`

## Quality

- `mitigation_addresses_hazard`
- `mitigation_actionable`
- `mitigation_specific`
- `legal_basis_relevant`
- `unsafe_advice`

## Safety

- `critical_safety_error`

## 무결성

이 표본은 sealed source run 바깥의 `derived/`에 생성되며, source run manifest SHA-256, run seal root SHA-256, 각 CSV의 비라벨 표본 identity SHA-256에 바인딩됩니다. 라벨·adjudication·notes 외의 표본 내용을 수정하면 calibration gate가 실패합니다.
""",
        encoding="utf-8",
    )

    source_manifest = run_dir / "manifest.json"
    manifest_path = output_dir / "binary_calibration_manifest.json"
    atomic_write_json(
        manifest_path,
        {
            "protocol": "binary-human-calibration-v1",
            "source_run": run_dir.name,
            "source_run_manifest_sha256": sha256_file(source_manifest) if source_manifest.exists() else None,
            "source_run_seal_verified": bool(source_verification.get("ok")),
            "source_run_seal_root_sha256": source_verification.get("artifact_root_sha256"),
            "seed": seed,
            "judge_scores_exposed_to_humans": False,
            "sampling": {
                "match": "fixed-seed balance by deterministic accident-label-overlap proxy; no Judge labels used",
                "quality": "fixed-seed sample from pairs for which the official pipeline produced quality records; Judge quality booleans hidden",
                "safety": "fixed-seed sample from generated risks; Judge safety booleans hidden",
            },
            "available_rows": {"match": len(matches), "quality": len(quality), "safety": len(safety)},
            "sampled_rows": {"match": len(selected_matches), "quality": len(selected_quality), "safety": len(selected_safety)},
            "sample_identity": {
                "match": {
                    "fields": match_identity_fields,
                    "sha256": _sample_identity_sha256(match_public, match_identity_fields),
                },
                "quality": {
                    "fields": quality_identity_fields,
                    "sha256": _sample_identity_sha256(quality_public, quality_identity_fields),
                },
                "safety": {
                    "fields": safety_identity_fields,
                    "sha256": _sample_identity_sha256(safety_public, safety_identity_fields),
                },
            },
            "dimensions": {
                "match": list(MATCH_DIMENSIONS),
                "quality": list(QUALITY_DIMENSIONS),
                "safety": list(SAFETY_DIMENSIONS),
                "primary_composite": PRIMARY_COMPOSITE,
            },
        },
    )
    return {
        "match": match_path,
        "quality": quality_path,
        "safety": safety_path,
        "instructions": instructions,
        "manifest": manifest_path,
    }


def _judge_maps(run_dir: Path) -> tuple[dict[tuple[str, str, str], dict[str, bool]], dict[tuple[str, str, str], dict[str, bool]], dict[tuple[str, str], dict[str, bool]]]:
    match_map: dict[tuple[str, str, str], dict[str, bool]] = {}
    quality_map: dict[tuple[str, str, str], dict[str, bool]] = {}
    safety_map: dict[tuple[str, str], dict[str, bool]] = {}
    for path in sorted((run_dir / "cases").glob("case-*/binary_judge.json")):
        case_id = path.parent.name
        evaluation = load_json(path).get("evaluation") or {}
        for row in evaluation.get("match_matrix") or []:
            key = (case_id, str(row["reference_id"]), str(row["generated_id"]))
            match_map[key] = {dimension: bool(row.get(dimension)) for dimension in MATCH_DIMENSIONS}
        for row in evaluation.get("quality") or []:
            key = (case_id, str(row["reference_id"]), str(row["generated_id"]))
            quality_map[key] = {dimension: bool(row.get(dimension)) for dimension in QUALITY_DIMENSIONS}
        for row in evaluation.get("safety") or []:
            key = (case_id, str(row["generated_id"]))
            safety_map[key] = {"critical_safety_error": bool(row.get("critical_safety_error"))}
    return match_map, quality_map, safety_map


def _score_boolean_rows(
    rows: list[dict[str, str]],
    *,
    dimensions: tuple[str, ...],
    lookup: Any,
    key_fields: tuple[str, ...],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for dimension in dimensions:
        r1s: list[int] = []
        r2s: list[int] = []
        humans: list[int] = []
        judges: list[int] = []
        resolved = 0
        missing_judge = 0
        applicable = 0
        for row in rows:
            if dimension == "legal_basis_relevant" and not str(row.get("generated_legal_basis") or "").strip():
                continue
            applicable += 1
            r1 = _parse_bool(row.get(f"rater1_{dimension}", ""))
            r2 = _parse_bool(row.get(f"rater2_{dimension}", ""))
            adj = _parse_bool(row.get(f"adjudicated_{dimension}", ""))
            if r1 is not None and r2 is not None:
                r1s.append(r1); r2s.append(r2)
            target, ok = _resolve(r1, r2, adj)
            if not ok or target is None:
                continue
            resolved += 1
            key = tuple(str(row[field]) for field in key_fields)
            judge = lookup.get(key)
            if judge is None or dimension not in judge:
                missing_judge += 1
                continue
            humans.append(target)
            judges.append(int(bool(judge[dimension])))
        output[dimension] = {
            "applicable_rows": applicable,
            "resolved_rows": resolved,
            "label_completion": resolved / applicable if applicable else None,
            "missing_judge_rows": missing_judge,
            "sample_count": len(humans),
            "human_human_agreement": _agreement(r1s, r2s),
            "human_human_kappa": _kappa(r1s, r2s),
            "judge_human_agreement": _agreement(judges, humans),
            "judge_human_kappa": _kappa(judges, humans),
            "human_positive_rate": sum(humans) / len(humans) if humans else None,
            "judge_positive_rate": sum(judges) / len(judges) if judges else None,
        }
    return output


def _score_primary_composite(rows: list[dict[str, str]], match_map: dict[tuple[str, str, str], dict[str, bool]]) -> dict[str, Any]:
    r1s: list[int] = []
    r2s: list[int] = []
    humans: list[int] = []
    judges: list[int] = []
    resolved = 0
    missing = 0
    for row in rows:
        m1 = _parse_bool(row.get("rater1_same_hazard_mechanism", ""))
        c1 = _parse_bool(row.get("rater1_context_compatible", ""))
        m2 = _parse_bool(row.get("rater2_same_hazard_mechanism", ""))
        c2 = _parse_bool(row.get("rater2_context_compatible", ""))
        ma = _parse_bool(row.get("adjudicated_same_hazard_mechanism", ""))
        ca = _parse_bool(row.get("adjudicated_context_compatible", ""))
        if m1 is not None and c1 is not None and m2 is not None and c2 is not None:
            r1s.append(int(bool(m1 and c1))); r2s.append(int(bool(m2 and c2)))
        target_m, ok_m = _resolve(m1, m2, ma)
        target_c, ok_c = _resolve(c1, c2, ca)
        if not (ok_m and ok_c) or target_m is None or target_c is None:
            continue
        resolved += 1
        key = (str(row["case_id"]), str(row["reference_id"]), str(row["generated_id"]))
        judge = match_map.get(key)
        if judge is None:
            missing += 1
            continue
        humans.append(int(bool(target_m and target_c)))
        judges.append(int(bool(judge["same_hazard_mechanism"] and judge["context_compatible"])))
    return {
        "applicable_rows": len(rows),
        "resolved_rows": resolved,
        "label_completion": resolved / len(rows) if rows else None,
        "missing_judge_rows": missing,
        "sample_count": len(humans),
        "human_human_agreement": _agreement(r1s, r2s),
        "human_human_kappa": _kappa(r1s, r2s),
        "judge_human_agreement": _agreement(judges, humans),
        "judge_human_kappa": _kappa(judges, humans),
        "human_positive_rate": sum(humans) / len(humans) if humans else None,
        "judge_positive_rate": sum(judges) / len(judges) if judges else None,
    }


def _binary_structured_completion(run_dir: Path) -> dict[str, Any]:
    expected_match = completed_match = expected_quality = completed_quality = expected_safety = completed_safety = 0
    for case_dir in sorted((run_dir / "cases").glob("case-*")):
        result_path = case_dir / "result.json"
        parsed_path = case_dir / "parsed.json"
        judge_path = case_dir / "binary_judge.json"
        if not (result_path.exists() and parsed_path.exists() and judge_path.exists()):
            continue
        result = load_json(result_path)
        parsed = ParsedRiskAssessment.model_validate(load_json(parsed_path)["parsed"])
        evaluation = load_json(judge_path).get("evaluation") or {}
        expected_match += int(result.get("reference_count") or 0) * len(parsed.risks)
        completed_match += len(evaluation.get("match_matrix") or [])
        expected_quality += len(evaluation.get("matches") or [])
        completed_quality += len(evaluation.get("quality") or [])
        expected_safety += len(parsed.risks)
        completed_safety += len(evaluation.get("safety") or [])
    def item(done: int, expected: int) -> dict[str, Any]:
        return {"completed": done, "expected": expected, "rate": done / expected if expected else None}
    rows = {
        "match_matrix": item(completed_match, expected_match),
        "matched_quality": item(completed_quality, expected_quality),
        "generated_safety": item(completed_safety, expected_safety),
    }
    rates = [row["rate"] for row in rows.values() if row["rate"] is not None]
    return {**rows, "minimum_rate": min(rates) if rates else None}


def score_binary_human_calibration(
    *,
    run_dir: Path,
    match_csv: Path,
    quality_csv: Path,
    safety_csv: Path,
    calibration_manifest: Path | None = None,
    primary_agreement_min: float = 0.90,
    primary_kappa_min: float = 0.70,
    dimension_agreement_min: float = 0.85,
    dimension_kappa_min: float = 0.60,
    safety_agreement_min: float = 0.90,
    human_label_completion_min: float = 1.0,
    structured_completion_min: float = 0.99,
    min_match_samples: int = 30,
    min_quality_samples: int = 30,
    min_safety_samples: int = 30,
) -> dict[str, Any]:
    match_rows = _read_csv(match_csv)
    quality_rows = _read_csv(quality_csv)
    safety_rows = _read_csv(safety_csv)
    calibration_manifest = calibration_manifest or match_csv.parent / "binary_calibration_manifest.json"
    if not calibration_manifest.exists():
        raise FileNotFoundError(f"Binary calibration manifest not found: {calibration_manifest}")
    calibration_meta = load_json(calibration_manifest)
    source_manifest = run_dir / "manifest.json"
    source_verification = verify_run(run_dir)
    sample_identity = calibration_meta.get("sample_identity") or {}
    identity_checks: dict[str, bool] = {}
    for name, path in (("match", match_csv), ("quality", quality_csv), ("safety", safety_csv)):
        meta = sample_identity.get(name) or {}
        fields = meta.get("fields") or []
        expected = meta.get("sha256")
        identity_checks[name] = bool(fields and expected and _csv_identity_sha256(path, list(fields)) == expected)
    binding_checks = {
        "calibration_protocol": calibration_meta.get("protocol") == "binary-human-calibration-v1",
        "source_run_id": calibration_meta.get("source_run") == run_dir.name,
        "source_run_manifest_sha256": bool(
            source_manifest.exists()
            and calibration_meta.get("source_run_manifest_sha256") == sha256_file(source_manifest)
        ),
        "source_run_seal_verified": bool(source_verification.get("ok")),
        "source_run_seal_root_sha256": (
            calibration_meta.get("source_run_seal_root_sha256")
            == source_verification.get("artifact_root_sha256")
        ),
        "match_sample_identity": identity_checks.get("match", False),
        "quality_sample_identity": identity_checks.get("quality", False),
        "safety_sample_identity": identity_checks.get("safety", False),
    }
    match_map, quality_map, safety_map = _judge_maps(run_dir)
    match_scores = _score_boolean_rows(
        match_rows, dimensions=MATCH_DIMENSIONS, lookup=match_map,
        key_fields=("case_id", "reference_id", "generated_id"),
    )
    quality_scores = _score_boolean_rows(
        quality_rows, dimensions=QUALITY_DIMENSIONS, lookup=quality_map,
        key_fields=("case_id", "reference_id", "generated_id"),
    )
    safety_scores = _score_boolean_rows(
        safety_rows, dimensions=SAFETY_DIMENSIONS, lookup=safety_map,
        key_fields=("case_id", "generated_id"),
    )
    primary = _score_primary_composite(match_rows, match_map)
    structured = _binary_structured_completion(run_dir)

    checks: dict[str, Any] = {}
    for name, passed in binding_checks.items():
        checks[f"binding_{name}"] = {
            "value": bool(passed),
            "minimum": True,
            "pass": bool(passed),
        }
    checks["primary_semantic_agreement"] = {
        "value": primary["judge_human_agreement"], "minimum": primary_agreement_min,
        "pass": primary["judge_human_agreement"] is not None and primary["judge_human_agreement"] >= primary_agreement_min,
    }
    checks["primary_semantic_kappa"] = {
        "value": primary["judge_human_kappa"], "minimum": primary_kappa_min,
        "pass": primary["judge_human_kappa"] is not None and primary["judge_human_kappa"] >= primary_kappa_min,
    }
    for group, scores in (("match", match_scores), ("quality", quality_scores)):
        for dimension, score in scores.items():
            agreement = score["judge_human_agreement"]
            kappa = score["judge_human_kappa"]
            checks[f"{group}_{dimension}_agreement"] = {
                "value": agreement, "minimum": dimension_agreement_min,
                "pass": agreement is not None and agreement >= dimension_agreement_min,
            }
            checks[f"{group}_{dimension}_kappa"] = {
                "value": kappa, "minimum": dimension_kappa_min,
                "pass": kappa is not None and kappa >= dimension_kappa_min,
            }
    safety = safety_scores["critical_safety_error"]
    checks["safety_critical_error_agreement"] = {
        "value": safety["judge_human_agreement"], "minimum": safety_agreement_min,
        "pass": safety["judge_human_agreement"] is not None and safety["judge_human_agreement"] >= safety_agreement_min,
        "note": "Kappa is reported but not a hard gate because a rare critical-error prevalence can make kappa unstable.",
    }

    all_scores = [primary, *match_scores.values(), *quality_scores.values(), *safety_scores.values()]
    completion = min(
        (score["label_completion"] for score in all_scores if score["applicable_rows"] and score["label_completion"] is not None),
        default=None,
    )
    checks["human_label_completion"] = {
        "value": completion, "minimum": human_label_completion_min,
        "pass": completion is not None and completion >= human_label_completion_min,
    }
    sample_checks = {
        "match_sample_size": (min((s["sample_count"] for s in match_scores.values()), default=0), min_match_samples),
        "quality_sample_size": (min((s["sample_count"] for s in quality_scores.values()), default=0), min_quality_samples),
        "safety_sample_size": (safety["sample_count"], min_safety_samples),
    }
    for name, (value, minimum) in sample_checks.items():
        checks[name] = {"value": value, "minimum": minimum, "pass": value >= minimum}
    checks["structured_completion"] = {
        "value": structured["minimum_rate"], "minimum": structured_completion_min,
        "pass": structured["minimum_rate"] is not None and structured["minimum_rate"] >= structured_completion_min,
    }

    source_manifest = run_dir / "manifest.json"
    output = {
        "protocol": "binary-human-calibration-v1",
        "source_run": run_dir.name,
        "source_run_manifest_sha256": sha256_file(source_manifest) if source_manifest.exists() else None,
        "source_run_seal_root_sha256": source_verification.get("artifact_root_sha256"),
        "calibration_manifest_sha256": sha256_file(calibration_manifest),
        "primary_composite": primary,
        "match_dimensions": match_scores,
        "quality_dimensions": quality_scores,
        "safety_dimensions": safety_scores,
        "structured_completion": structured,
        "checks": checks,
        "gate_pass": all(bool(check.get("pass")) for check in checks.values()),
    }
    return output
