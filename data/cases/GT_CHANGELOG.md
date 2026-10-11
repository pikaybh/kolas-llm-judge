# KOLAS_RA_GT Change Log

## KOLAS_RA_GT v1.0.0

### 2026-09-08 — legacy dataset imported into reproducible harness

- Legacy KOLAS `v7_73` XLSX dataset was transferred to the canonical processing representation (`CSV -> bzip2`).
- Original workbook recorded SHA-256: `d12c7d683518b680615e2311f49059ed3f5c439cf6c706afb671b6c7bcafdd4a`.
- Canonical transfer representation SHA-256: `b76c9efa718a0429f587b311d9e6e1d2107bf13101b0f91bc02a69e695ad142a`.
- 843 source rows were deterministically grouped into 425 scenarios without dropping source rows.

### 2026-09-14 — explicit dataset identity added

- Added `dataset_id=KOLAS_RA_GT`, `dataset_version=1.0.0`, and `schema_version=kolas-ra-dataset-v1` to the dataset manifest.
- Raw GT and scenario content hashes did not change.

### 2026-10-11 — Phase 3 provenance audit

- Rebuilt `scenarios_v1.jsonl` from the frozen raw representation and confirmed byte-identical output.
- Added `gt_lineage_index_v1.csv` covering source rows 2..844 exactly once.
- Added `gt_provenance_register_v1.csv`, one row per reference, binding each row to frozen hazard content by SHA-256 without copying raw hazard text.
- Recorded authoritative safety-evidence provenance as unresolved for 843/843 references rather than inferring historical sources.
- Recorded duplicate/near-duplicate screening candidates for audit visibility; no reference was deleted or merged because the GT is already laboratory-reviewed and validated.
- Corrected transcription errors in the Phase 0 evidence inventory. Canonical GT content did not change.

## Versioning rule

- Existing `v1.0.0` raw/scenario artifacts are immutable.
- Provenance-only enrichment may increase a separate provenance revision while keeping dataset content version `1.0.0` if reference content and IDs remain unchanged.
- Any substantive GT content or grouping change requires a new dataset version and explicit old-to-new reference mapping.
- Row insertion, deletion, or reordering must not silently regenerate accredited identifiers.
- GT and provenance artifacts are frozen when the accredited test begins.
