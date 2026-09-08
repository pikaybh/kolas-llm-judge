from __future__ import annotations

import asyncio
from pathlib import Path

from kolas_llm_judge.io_utils import load_json
from kolas_llm_judge.judge import JudgeCallRecord
from kolas_llm_judge.models import (
    CaseJudgeResult,
    EvaluationScenario,
    GeneratedJudgeResult,
    PairJudgeResult,
    ReferenceRisk,
    ScenarioInput,
)
from kolas_llm_judge.report import build_summary, export_reports
from kolas_llm_judge.runner import process_case
from kolas_llm_judge.sut_client import SutConfig, SutRunResult


VALID_XML = """
<risk_assessment>
  <method>빈도강도법 5x4</method>
  <process_name>철근 조립</process_name>
  <equipment>절단기</equipment>
  <material>철근</material>
  <items>
    <item>
      <id>1</id>
      <hazard_primary_category>철근공사</hazard_primary_category>
      <hazard_secondary_category>베임</hazard_secondary_category>
      <accident_classification>베임</accident_classification>
      <risk_category>조립</risk_category>
      <risk_cause>절단날 접촉</risk_cause>
      <hazard>회전 절단날 접촉으로 베일 위험</hazard>
      <prob_freq>2</prob_freq>
      <severity>2</severity>
      <risk_level>4</risk_level>
      <reduction_measures_detail>방호덮개 설치</reduction_measures_detail>
      <post_improvement_prob_freq>1</post_improvement_prob_freq>
      <post_improvement_severity>2</post_improvement_severity>
      <post_improvement_risk_level>2</post_improvement_risk_level>
      <basis>산업안전보건기준에 관한 규칙</basis>
    </item>
  </items>
</risk_assessment>
"""


class FakeSut:
    def __init__(self) -> None:
        self.calls = 0
        self.config = SutConfig(model_mode="pro")

    async def run_case(self, scenario, *, client_request_id=None):
        self.calls += 1
        return SutRunResult(
            case_id=scenario.case_id,
            session_id="session-1",
            run_id="run-1",
            content=VALID_XML,
            elapsed_ms=123,
            events=[{"type": "run-completed", "content": VALID_XML}],
            create_run_attempts=2,
            stream_reconnects=1,
            retry_log=[
                {"stage": "create_run"},
                {"stage": "sse"},
                {"stage": "auth", "action": "refresh"},
            ],
            auth_recoveries=1,
        )


class FakeJudge:
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate_case(self, scenario, generated):
        self.calls += 1
        pair = PairJudgeResult(
            reference_id=scenario.references[0].reference_id,
            generated_id=generated[0].generated_id,
            semantic_match=4,
            accident_type_correctness=2,
            mitigation_appropriateness=2,
            mitigation_specificity=2,
            legal_basis_relevance=2,
            explanation="동일 위험",
        )
        item = GeneratedJudgeResult(
            generated_id=generated[0].generated_id,
            unsupported_claim=False,
            critical_safety_error=False,
            explanation="근거 있음",
        )
        result = CaseJudgeResult(
            pair_evaluations=[pair],
            generated_evaluations=[item],
        )
        return JudgeCallRecord(
            result=result,
            response_id="judge-1",
            response_model="fake",
            usage={
                "input_tokens": 6,
                "output_tokens": 4,
                "total_tokens": 10,
                "input_tokens_details": {"cached_tokens": 2},
                "output_tokens_details": {"reasoning_tokens": 1},
            },
            calls=[
                {
                    "response_id": "judge-1",
                    "response_model": "fake",
                    "usage": {
                        "input_tokens": 6,
                        "output_tokens": 4,
                        "total_tokens": 10,
                        "input_tokens_details": {"cached_tokens": 2},
                        "output_tokens_details": {"reasoning_tokens": 1},
                    },
                }
            ],
        )


def _scenario() -> EvaluationScenario:
    return EvaluationScenario(
        case_id="case-test",
        source_rows=[2],
        input=ScenarioInput(
            process="철근공사",
            subprocess="조립",
            equipment=["절단기"],
            materials=["철근"],
        ),
        references=[
            ReferenceRisk(
                reference_id="case-test-r2",
                source_row=2,
                hazard="절단기 날 접촉으로 베임",
                accident_types=["베임"],
                mitigation="방호덮개 설치",
                legal_basis="산업안전보건기준에 관한 규칙",
            )
        ],
    )


def test_process_case_checkpoints_and_resume(tmp_path: Path) -> None:
    sut = FakeSut()
    judge = FakeJudge()
    scenario = _scenario()

    stages: list[str] = []
    status = asyncio.run(
        process_case(
            scenario=scenario,
            run_dir=tmp_path,
            evaluation_run_id="eval-1",
            sut=sut,
            judge=judge,
            progress_callback=stages.append,
        )
    )
    assert status == "completed"
    assert stages == ["sut", "parse", "judge", "matching"]
    assert sut.calls == 1
    assert judge.calls == 1

    case_dir = tmp_path / "cases/case-test"
    assert (case_dir / "sut.json").exists()
    assert (case_dir / "parsed.json").exists()
    assert (case_dir / "judge.json").exists()
    assert (case_dir / "result.json").exists()

    status = asyncio.run(
        process_case(
            scenario=scenario,
            run_dir=tmp_path,
            evaluation_run_id="eval-1",
            sut=sut,
            judge=judge,
        )
    )
    assert status == "skipped"
    assert sut.calls == 1
    assert judge.calls == 1

    # Simulate loss of only the final aggregate checkpoint.
    (case_dir / "result.json").unlink()
    status = asyncio.run(
        process_case(
            scenario=scenario,
            run_dir=tmp_path,
            evaluation_run_id="eval-1",
            sut=sut,
            judge=judge,
        )
    )
    assert status == "completed"
    assert sut.calls == 1
    assert judge.calls == 1


def test_report_aggregation(tmp_path: Path) -> None:
    sut = FakeSut()
    judge = FakeJudge()
    scenario = _scenario()
    asyncio.run(
        process_case(
            scenario=scenario,
            run_dir=tmp_path,
            evaluation_run_id="eval-1",
            sut=sut,
            judge=judge,
        )
    )
    from kolas_llm_judge.io_utils import atomic_write_json

    atomic_write_json(
        tmp_path / "manifest.json",
        {
            "run_id": "eval-1",
            "mode": "smoke",
            "selected_case_count": 1,
        },
    )
    summary = build_summary(tmp_path)
    assert summary["completed_cases"] == 1
    assert summary["metrics"]["reference_risk_coverage"]["rate"] == 1.0
    assert summary["schema_compliance"]["rate"] == 1.0
    assert summary["sut_runtime"]["latency_ms"]["mean"] == 123.0
    assert summary["sut_runtime"]["latency_ms"]["median"] == 123.0
    assert summary["sut_runtime"]["latency_ms"]["p95"] == 123.0
    assert summary["sut_runtime"]["retries"]["total_retry_count"] == 3
    assert summary["sut_runtime"]["retries"]["create_run_retry_count"] == 1
    assert summary["sut_runtime"]["retries"]["stream_reconnect_count"] == 1
    assert summary["sut_runtime"]["retries"]["auth_recovery_count"] == 1
    assert summary["judge_usage"]["call_count"] == 1
    assert summary["judge_usage"]["input_tokens"] == 6
    assert summary["judge_usage"]["output_tokens"] == 4
    assert summary["judge_usage"]["total_tokens"] == 10
    assert summary["judge_usage"]["reasoning_tokens"] == 1
    assert summary["judge_usage"]["cached_input_tokens"] == 2

    paths = export_reports(tmp_path)
    assert all(path.exists() for path in paths.values())
    saved = load_json(paths["summary"])
    assert saved["run_id"] == "eval-1"
