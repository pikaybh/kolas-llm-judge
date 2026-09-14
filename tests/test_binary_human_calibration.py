from __future__ import annotations

import csv
from pathlib import Path

from kolas_llm_judge.binary_human_calibration import (
    MATCH_DIMENSIONS,
    QUALITY_DIMENSIONS,
    SAFETY_DIMENSIONS,
    make_binary_human_calibration_template,
    score_binary_human_calibration,
)
from kolas_llm_judge.io_utils import atomic_write_json
from kolas_llm_judge.models import EvaluationScenario, ReferenceRisk, ScenarioInput
from kolas_llm_judge.seal import seal_run


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    run = tmp_path / "run"
    case = run / "cases/case-binary"
    case.mkdir(parents=True)
    scenario = EvaluationScenario(
        case_id="case-binary",
        source_rows=[2],
        input=ScenarioInput(process="전기", subprocess="배선", equipment=["분전반"], materials=["전선"]),
        references=[ReferenceRisk(reference_id="case-binary-r2", source_row=2, hazard="활선 접촉 감전", accident_types=["감전"], mitigation="전원 차단", legal_basis="제1조")],
    )
    scenarios = tmp_path / "scenarios.jsonl"
    scenarios.write_text(scenario.model_dump_json() + "\n", encoding="utf-8")
    atomic_write_json(case / "parsed.json", {"parsed": {"method":"빈도강도법 5x4", "risks":[{"generated_id":"g001","hazard":"활선 접촉으로 감전","risk_cause":"활선 접촉","accident_types":["감전"],"mitigation":"전원 차단 후 무전압 확인","legal_basis":"제1조","likelihood":2,"severity":4,"risk_score":8,"post_improvement_numeric_tags_present":False,"post_improvement_numeric_tags_blank":False,"post_improvement_verbal_tag_present":False,"post_improvement_verbal_tag_blank":False}], "xml":"<risk_assessment/>", "equipment":[], "materials":[], "trailing_text":""}})
    atomic_write_json(case / "result.json", {"case_id":"case-binary","status":"completed","reference_count":1,"metrics":{}})
    atomic_write_json(case / "binary_judge.json", {"evaluation": {"match_matrix":[{"reference_id":"case-binary-r2","generated_id":"g001","same_hazard_mechanism":True,"context_compatible":True,"accident_compatible":True}], "matches":[{"reference_id":"case-binary-r2","generated_id":"g001","same_hazard_mechanism":True,"context_compatible":True,"accident_compatible":True}], "quality":[{"reference_id":"case-binary-r2","generated_id":"g001","mitigation_addresses_hazard":True,"mitigation_actionable":True,"mitigation_specific":True,"legal_basis_relevant":True,"unsafe_advice":False}], "safety":[{"generated_id":"g001","critical_safety_error":False}], "metrics":{}, "calls":[]}})
    atomic_write_json(run / "manifest.json", {"run_id":"binary-fixture","method_identity":{"x":1}})
    seal_run(run)
    return run, scenarios


def _fill(path: Path, dimensions: tuple[str, ...], values: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys())
    for row in rows:
        for dimension in dimensions:
            value=values[dimension]
            row[f"rater1_{dimension}"]=value
            row[f"rater2_{dimension}"]=value
            row[f"adjudicated_{dimension}"]=value
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def test_binary_calibration_template_and_gate(tmp_path: Path) -> None:
    run, scenarios = _fixture(tmp_path)
    paths = make_binary_human_calibration_template(run_dir=run, scenarios_path=scenarios, output_dir=tmp_path/"calibration", match_sample_size=1, quality_sample_size=1, safety_sample_size=1)
    text=paths["match"].read_text(encoding="utf-8-sig")
    assert "judge" not in text.lower()
    _fill(paths["match"], MATCH_DIMENSIONS, {d:"1" for d in MATCH_DIMENSIONS})
    _fill(paths["quality"], QUALITY_DIMENSIONS, {"mitigation_addresses_hazard":"1","mitigation_actionable":"1","mitigation_specific":"1","legal_basis_relevant":"1","unsafe_advice":"0"})
    _fill(paths["safety"], SAFETY_DIMENSIONS, {"critical_safety_error":"0"})
    result=score_binary_human_calibration(run_dir=run, match_csv=paths["match"], quality_csv=paths["quality"], safety_csv=paths["safety"], min_match_samples=1, min_quality_samples=1, min_safety_samples=1)
    assert result["primary_composite"]["judge_human_agreement"] == 1.0
    assert result["gate_pass"] is True


def test_binary_calibration_detects_primary_disagreement(tmp_path: Path) -> None:
    run, scenarios = _fixture(tmp_path)
    paths=make_binary_human_calibration_template(run_dir=run, scenarios_path=scenarios, output_dir=tmp_path/"calibration", match_sample_size=1, quality_sample_size=1, safety_sample_size=1)
    _fill(paths["match"], MATCH_DIMENSIONS, {"same_hazard_mechanism":"0","context_compatible":"1","accident_compatible":"1"})
    _fill(paths["quality"], QUALITY_DIMENSIONS, {"mitigation_addresses_hazard":"1","mitigation_actionable":"1","mitigation_specific":"1","legal_basis_relevant":"1","unsafe_advice":"0"})
    _fill(paths["safety"], SAFETY_DIMENSIONS, {"critical_safety_error":"0"})
    result=score_binary_human_calibration(run_dir=run, match_csv=paths["match"], quality_csv=paths["quality"], safety_csv=paths["safety"], min_match_samples=1, min_quality_samples=1, min_safety_samples=1)
    assert result["checks"]["primary_semantic_agreement"]["pass"] is False
    assert result["gate_pass"] is False


def test_binary_calibration_does_not_mutate_sealed_run(tmp_path: Path) -> None:
    run, scenarios = _fixture(tmp_path)
    before = (run / "run_seal.json").read_bytes()
    make_binary_human_calibration_template(
        run_dir=run, scenarios_path=scenarios, output_dir=tmp_path/"derived",
        match_sample_size=1, quality_sample_size=1, safety_sample_size=1,
    )
    assert (run / "run_seal.json").read_bytes() == before
    from kolas_llm_judge.seal import verify_run
    assert verify_run(run)["ok"] is True


def test_binary_calibration_rejects_sample_identity_tamper(tmp_path: Path) -> None:
    run, scenarios = _fixture(tmp_path)
    paths = make_binary_human_calibration_template(
        run_dir=run, scenarios_path=scenarios, output_dir=tmp_path/"calibration",
        match_sample_size=1, quality_sample_size=1, safety_sample_size=1,
    )
    _fill(paths["match"], MATCH_DIMENSIONS, {d:"1" for d in MATCH_DIMENSIONS})
    _fill(paths["quality"], QUALITY_DIMENSIONS, {"mitigation_addresses_hazard":"1","mitigation_actionable":"1","mitigation_specific":"1","legal_basis_relevant":"1","unsafe_advice":"0"})
    _fill(paths["safety"], SAFETY_DIMENSIONS, {"critical_safety_error":"0"})
    with paths["match"].open("r", encoding="utf-8-sig", newline="") as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys())
    rows[0]["generated_hazard"] = "TAMPERED SAMPLE CONTENT"
    with paths["match"].open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    result = score_binary_human_calibration(
        run_dir=run, match_csv=paths["match"], quality_csv=paths["quality"], safety_csv=paths["safety"],
        min_match_samples=1, min_quality_samples=1, min_safety_samples=1,
    )
    assert result["checks"]["binding_match_sample_identity"]["pass"] is False
    assert result["gate_pass"] is False
