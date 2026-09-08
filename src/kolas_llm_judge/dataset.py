from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from .models import DatasetManifest, EvaluationScenario, ReferenceRisk, ScenarioInput

REQUIRED_COLUMNS = [
    "공정", "세부공정", "설비", "물질", "유해위험요인", "사고분류",
    "위험 가능성", "위험 중대성", "위험성", "감소대책", "관련근거(법규)",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        cleaned = _clean(value)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _first_int(value: object) -> int | None:
    text = _clean(value)
    if not text:
        return None
    in_parens = re.search(r"\((\d+)\)", text)
    if in_parens:
        return int(in_parens.group(1))
    any_int = re.search(r"\d+", text)
    return int(any_int.group()) if any_int else None


def _split_accidents(value: object) -> list[str]:
    return [part.strip() for part in _clean(value).split(";") if part.strip()]


def _case_id(process: str, subprocess: str) -> str:
    raw = json.dumps({"process": process, "subprocess": subprocess}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "case-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def validate_source(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df.empty:
        raise ValueError("Dataset is empty")
    if df["공정"].isna().any():
        raise ValueError("공정 contains null values")
    if df["유해위험요인"].isna().any():
        raise ValueError("유해위험요인 contains null values")


def build_scenarios(df: pd.DataFrame) -> list[EvaluationScenario]:
    validate_source(df)
    work = df.copy()
    work["_source_row"] = range(2, len(work) + 2)
    work["_process"] = work["공정"].map(_clean)
    work["_subprocess"] = work["세부공정"].map(_clean)

    scenarios: list[EvaluationScenario] = []
    grouped = work.groupby(["_process", "_subprocess"], sort=False, dropna=False)
    for (process, subprocess), group in grouped:
        case_id = _case_id(process, subprocess)
        references: list[ReferenceRisk] = []
        for _, row in group.iterrows():
            source_row = int(row["_source_row"])
            references.append(ReferenceRisk(
                reference_id=f"{case_id}-r{source_row}",
                source_row=source_row,
                hazard=_clean(row["유해위험요인"]),
                accident_types=_split_accidents(row["사고분류"]),
                likelihood=_first_int(row["위험 가능성"]),
                severity=_first_int(row["위험 중대성"]),
                risk_score=_first_int(row["위험성"]),
                mitigation=_clean(row["감소대책"]) or None,
                legal_basis=_clean(row["관련근거(법규)"]) or None,
            ))

        scenario_input = ScenarioInput(
            process=process,
            subprocess=subprocess or None,
            equipment=_unique(group["설비"].tolist()),
            materials=_unique(group["물질"].tolist()),
        )
        scenarios.append(EvaluationScenario(
            case_id=case_id,
            source_rows=[int(v) for v in group["_source_row"].tolist()],
            input=scenario_input,
            references=references,
        ))
    return scenarios


def write_jsonl(scenarios: list[EvaluationScenario], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for scenario in scenarios:
            f.write(json.dumps(scenario.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def read_source_dataframe(source: Path) -> pd.DataFrame:
    name = source.name.lower()
    if name.endswith((".csv", ".csv.gz", ".csv.bz2", ".csv.xz")):
        return pd.read_csv(source)
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return pd.read_excel(source)
    raise ValueError(f"Unsupported dataset format: {source.name}")


def import_dataset(source: Path, output: Path, manifest_path: Path, *, expected_rows: int | None = None, expected_scenarios: int | None = None) -> DatasetManifest:
    df = read_source_dataframe(source)
    validate_source(df)
    if expected_rows is not None and len(df) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, got {len(df)}")
    scenarios = build_scenarios(df)
    if expected_scenarios is not None and len(scenarios) != expected_scenarios:
        raise ValueError(f"Expected {expected_scenarios} scenarios, got {len(scenarios)}")
    write_jsonl(scenarios, output)
    manifest = DatasetManifest(
        source_file=str(source),
        source_sha256=sha256_file(source),
        source_rows=len(df),
        scenario_count=len(scenarios),
        reference_count=sum(len(s.references) for s in scenarios),
        grouping=["공정", "세부공정"],
        cases_sha256=sha256_file(output),
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
