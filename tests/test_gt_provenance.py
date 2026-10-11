from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kolas_llm_judge.dataset import sha256_file
from kolas_llm_judge.io_utils import load_scenarios
from tools.gt_provenance import (
    REGISTER_FIELDS,
    build_lineage_index,
    build_unresolved_provenance_register,
    sha256_text,
)

SCENARIOS = ROOT / "data/cases/scenarios_v1.jsonl"
TRANSFER = ROOT / "data/raw/kolas_v7_73_test.csv.bz2"
LINEAGE = ROOT / "data/cases/gt_lineage_index_v1.csv"
REGISTER = ROOT / "data/cases/gt_provenance_register_v1.csv"
AUDIT_MANIFEST = ROOT / "data/cases/gt_provenance_audit_manifest_v1.json"
SCHEMA = ROOT / "configs/gt_provenance_schema_v1.yaml"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _expected_references() -> dict[str, tuple[str, int, str]]:
    return {
        reference.reference_id: (
            scenario.case_id,
            reference.source_row,
            sha256_text(reference.hazard),
        )
        for scenario in load_scenarios(SCENARIOS)
        for reference in scenario.references
    }


def test_lineage_index_covers_every_frozen_reference() -> None:
    lineage = _rows(LINEAGE)
    expected = _expected_references()
    assert len(lineage) == 843
    assert len(expected) == 843
    assert {row["reference_id"] for row in lineage} == set(expected)
    assert [int(row["source_row"]) for row in lineage] == list(range(2, 845))
    for row in lineage:
        case_id, source_row, _ = expected[row["reference_id"]]
        assert row["case_id"] == case_id
        assert int(row["source_row"]) == source_row


def test_provenance_register_is_complete_and_explicitly_unresolved() -> None:
    register = _rows(REGISTER)
    expected = _expected_references()
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))

    assert len(register) == 843
    assert list(register[0]) == REGISTER_FIELDS
    assert list(register[0]) == schema["required_fields"]
    assert {row["reference_id"] for row in register} == set(expected)

    for row in register:
        case_id, source_row, hazard_sha256 = expected[row["reference_id"]]
        assert row["dataset_id"] == "KOLAS_RA_GT"
        assert row["dataset_version"] == "1.0.0"
        assert row["case_id"] == case_id
        assert int(row["source_row"]) == source_row
        assert row["reference_hazard_sha256"] == hazard_sha256
        assert row["lineage_origin"] == "legacy_kolas_v7_73_workbook"
        assert row["provenance_status"] == "unresolved"
        assert row["source_type"] == "LEGACY_WORKBOOK_ONLY"
        assert row["source_id"] == ""
        assert row["locator"] == ""
        assert row["source_sha256"] == ""
        assert row["license_status"] == "unknown"
        assert row["external_sharing"] == "unknown"
        assert row["expert_validation_status"] == "pending"


def test_provenance_register_does_not_copy_raw_hazard_text() -> None:
    with REGISTER.open("r", encoding="utf-8", newline="") as f:
        fieldnames = csv.DictReader(f).fieldnames
    assert fieldnames is not None
    assert "hazard" not in fieldnames
    assert "유해위험요인" not in fieldnames
    assert "reference_hazard_sha256" in fieldnames


def test_provenance_audit_manifest_matches_frozen_artifacts() -> None:
    manifest = json.loads(AUDIT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["dataset_id"] == "KOLAS_RA_GT"
    assert manifest["dataset_version"] == "1.0.0"
    assert manifest["status"] == "INCOMPLETE_LEGACY_PROVENANCE"
    assert manifest["original_workbook"]["status"] == (
        "recorded_hash_only_original_bytes_not_located"
    )
    assert manifest["original_workbook"]["recorded_sha256"] == (
        "d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a"
    )
    assert manifest["canonical_raw"]["sha256"] == sha256_file(TRANSFER)
    assert manifest["canonical_scenarios"]["sha256"] == sha256_file(SCENARIOS)
    assert manifest["lineage_index"]["sha256"] == sha256_file(LINEAGE)
    assert manifest["provenance_register"]["sha256"] == sha256_file(REGISTER)
    assert manifest["provenance_schema"]["sha256"] == sha256_file(SCHEMA)
    assert manifest["coverage"]["file_lineage"]["verified"] == 843
    assert manifest["coverage"]["authoritative_source"]["verified"] == 0
    assert manifest["coverage"]["expert_validated_source"]["verified"] == 0
    assert manifest["coverage"]["unresolved_source"]["count"] == 843
    assert manifest["provenance_register"]["contains_raw_hazard_text"] is False


def test_provenance_artifacts_rebuild_byte_identically(tmp_path: Path) -> None:
    rebuilt_lineage = tmp_path / "gt_lineage_index_v1.csv"
    rebuilt_register = tmp_path / "gt_provenance_register_v1.csv"
    build_lineage_index(scenarios_path=SCENARIOS, output_path=rebuilt_lineage)
    build_unresolved_provenance_register(
        scenarios_path=SCENARIOS,
        output_path=rebuilt_register,
    )
    assert rebuilt_lineage.read_bytes() == LINEAGE.read_bytes()
    assert rebuilt_register.read_bytes() == REGISTER.read_bytes()
