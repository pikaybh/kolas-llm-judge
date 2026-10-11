from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from kolas_llm_judge.io_utils import load_scenarios

LINEAGE_FIELDS = ["reference_id", "source_row", "case_id"]
REGISTER_FIELDS = [
    "dataset_id",
    "dataset_version",
    "case_id",
    "reference_id",
    "source_row",
    "reference_hazard_sha256",
    "lineage_origin",
    "provenance_status",
    "source_type",
    "source_id",
    "source_title",
    "issuer_author",
    "publication_date",
    "version_revision",
    "locator",
    "source_url",
    "archive_id",
    "source_sha256",
    "evidence_relation",
    "evidence_excerpt_hash",
    "license_status",
    "external_sharing",
    "verified_by",
    "verified_at",
    "expert_validation_status",
    "notes",
]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reference_rows(scenarios_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario in load_scenarios(scenarios_path):
        for reference in scenario.references:
            rows.append(
                {
                    "case_id": scenario.case_id,
                    "reference_id": reference.reference_id,
                    "source_row": reference.source_row,
                    "hazard": reference.hazard,
                }
            )
    rows.sort(key=lambda row: int(row["source_row"]))
    return rows


def build_lineage_index(*, scenarios_path: Path, output_path: Path) -> None:
    rows = _reference_rows(scenarios_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LINEAGE_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in LINEAGE_FIELDS})


def build_unresolved_provenance_register(
    *,
    scenarios_path: Path,
    output_path: Path,
    dataset_id: str = "KOLAS_RA_GT",
    dataset_version: str = "1.0.0",
) -> None:
    rows = _reference_rows(scenarios_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTER_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "dataset_id": dataset_id,
                    "dataset_version": dataset_version,
                    "case_id": row["case_id"],
                    "reference_id": row["reference_id"],
                    "source_row": row["source_row"],
                    "reference_hazard_sha256": sha256_text(str(row["hazard"])),
                    "lineage_origin": "legacy_kolas_v7_73_workbook",
                    "provenance_status": "unresolved",
                    "source_type": "LEGACY_WORKBOOK_ONLY",
                    "source_id": "",
                    "source_title": "",
                    "issuer_author": "",
                    "publication_date": "",
                    "version_revision": "",
                    "locator": "",
                    "source_url": "",
                    "archive_id": "",
                    "source_sha256": "",
                    "evidence_relation": "",
                    "evidence_excerpt_hash": "",
                    "license_status": "unknown",
                    "external_sharing": "unknown",
                    "verified_by": "",
                    "verified_at": "",
                    "expert_validation_status": "pending",
                    "notes": "",
                }
            )
