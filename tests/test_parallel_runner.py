import asyncio
from pathlib import Path

from kolas_llm_judge.binary_judge import (
    BinaryJudgeCall,
    MatchChecklistDecision,
    QualityChecklistDecision,
    SafetyChecklistDecision,
)
from kolas_llm_judge.models import (
    EvaluationScenario,
    ReferenceRisk,
    ScenarioInput,
)
from kolas_llm_judge.parallel_runner import (
    ParallelRunnerConfig,
    run_parallel_cases,
)
from kolas_llm_judge.sut_client import SutConfig, SutRunResult


FAST_XML = """
<risk_assessment>
  <method>빈도강도법 5x4</method>
  <items>
    <item>
      <id>1</id>
      <accident_classification>감전</accident_classification>
      <hazard>노출 충전부 접촉 감전 위험</hazard>
      <prob_freq>2</prob_freq>
      <severity>4</severity>
      <risk_level>8</risk_level>
      <reduction_measures_detail>전원 차단 및 무전압 확인</reduction_measures_detail>
      <post_improvement_prob_freq></post_improvement_prob_freq>
      <post_improvement_severity></post_improvement_severity>
      <post_improvement_risk_level></post_improvement_risk_level>
      <basis>전기작업 안전 관련 조항</basis>
    </item>
  </items>
</risk_assessment>
"""


class FakeParallelSut:
    def __init__(self, fail_case: str | None = None) -> None:
        self.config = SutConfig(model_mode="fast")
        self.active = 0
        self.max_active = 0
        self.calls = 0
        self.fail_case = fail_case

    async def run_case(self, scenario, *, client_request_id=None):
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.03)
            if scenario.case_id == self.fail_case:
                raise RuntimeError("synthetic SUT failure")
            return SutRunResult(
                case_id=scenario.case_id,
                session_id=f"session-{scenario.case_id}",
                run_id=f"run-{scenario.case_id}",
                content=FAST_XML,
                elapsed_ms=30,
                events=[],
            )
        finally:
            self.active -= 1


class FakeParallelJudge:
    async def evaluate_match_pairs(self, scenario, pairs):
        return BinaryJudgeCall(
            "match",
            [
                MatchChecklistDecision(
                    id=f"{ref.reference_id}::{risk.generated_id}",
                    same_hazard_mechanism=True,
                    context_compatible=True,
                    accident_compatible=True,
                )
                for ref, risk in pairs
            ],
            "m",
            "fake",
            {},
            1,
        )

    async def evaluate_quality_pairs(self, scenario, pairs):
        return BinaryJudgeCall(
            "quality",
            [
                QualityChecklistDecision(
                    id=f"{ref.reference_id}::{risk.generated_id}",
                    mitigation_addresses_hazard=True,
                    mitigation_actionable=True,
                    mitigation_specific=True,
                    unsafe_advice=False,
                    legal_basis_relevant=True,
                )
                for ref, risk in pairs
            ],
            "q",
            "fake",
            {},
            1,
        )

    async def evaluate_safety_risks(self, scenario, generated):
        return BinaryJudgeCall(
            "safety",
            [
                SafetyChecklistDecision(
                    id=risk.generated_id,
                    critical_safety_error=False,
                )
                for risk in generated
            ],
            "s",
            "fake",
            {},
            1,
        )


def scenarios(count: int) -> list[EvaluationScenario]:
    return [
        EvaluationScenario(
            case_id=f"case-{index:02d}",
            source_rows=[index + 2],
            input=ScenarioInput(process=f"전기작업-{index}"),
            references=[
                ReferenceRisk(
                    reference_id=f"ref-{index}",
                    source_row=index + 2,
                    hazard="노출 충전부 접촉 감전 위험",
                    accident_types=["감전"],
                    mitigation="전원 차단",
                    legal_basis="전기작업 안전 관련 조항",
                )
            ],
        )
        for index in range(count)
    ]


def test_parallel_runner_bounds_sut_concurrency_and_checkpoints(tmp_path: Path) -> None:
    sut = FakeParallelSut()
    selected = scenarios(6)
    summary = asyncio.run(
        run_parallel_cases(
            scenarios=selected,
            run_dir=tmp_path,
            evaluation_run_id="parallel-test",
            sut=sut,  # type: ignore[arg-type]
            judge=FakeParallelJudge(),  # type: ignore[arg-type]
            config=ParallelRunnerConfig(
                case_concurrency=4,
                sut_concurrency=2,
                match_chunk_size=2,
                quality_chunk_size=1,
                safety_chunk_size=1,
            ),
        )
    )
    assert summary.completed == 6
    assert summary.failed == 0
    assert sut.max_active == 2
    assert sut.calls == 6
    for scenario in selected:
        root = tmp_path / "cases" / scenario.case_id
        assert (root / "sut.json").exists()
        assert (root / "parsed.json").exists()
        assert (root / "binary_judge.json").exists()
        assert (root / "result.json").exists()

    resumed = asyncio.run(
        run_parallel_cases(
            scenarios=selected,
            run_dir=tmp_path,
            evaluation_run_id="parallel-test",
            sut=sut,  # type: ignore[arg-type]
            judge=FakeParallelJudge(),  # type: ignore[arg-type]
            config=ParallelRunnerConfig(case_concurrency=4, sut_concurrency=2),
        )
    )
    assert resumed.skipped == 6
    assert sut.calls == 6


def test_parallel_runner_records_one_case_failure_and_continues(tmp_path: Path) -> None:
    selected = scenarios(5)
    sut = FakeParallelSut(fail_case="case-02")
    summary = asyncio.run(
        run_parallel_cases(
            scenarios=selected,
            run_dir=tmp_path,
            evaluation_run_id="parallel-failure",
            sut=sut,  # type: ignore[arg-type]
            judge=FakeParallelJudge(),  # type: ignore[arg-type]
            config=ParallelRunnerConfig(case_concurrency=3, sut_concurrency=2),
            continue_on_error=True,
        )
    )
    assert summary.completed == 4
    assert summary.failed == 1
    error = tmp_path / "cases/case-02/error.json"
    assert error.exists()
    assert "synthetic SUT failure" in error.read_text(encoding="utf-8")


def test_failure_classifier_separates_sut_from_evaluator_failures() -> None:
    from kolas_llm_judge.parallel_runner import classify_failure

    assert classify_failure(
        stage="parse",
        exc=ValueError("<risk_assessment> XML block not found"),
        sut_content="<ask_user><question>추가 정보</question></ask_user>",
    ) == ("sut_non_completion", "ask_user")
    assert classify_failure(
        stage="parse",
        exc=ValueError("Invalid risk_assessment XML: broken"),
        sut_content="<risk_assessment><broken>",
    ) == ("sut_non_completion", "invalid_risk_assessment_xml")
    assert classify_failure(
        stage="binary_judge",
        exc=RuntimeError("OpenAI unavailable"),
    ) == ("evaluator_failure", "judge_or_evaluator_failure")
    assert classify_failure(
        stage="sut",
        exc=RuntimeError("transport exhausted"),
    ) == ("infrastructure_failure", "sut_transport_or_api_failure")
