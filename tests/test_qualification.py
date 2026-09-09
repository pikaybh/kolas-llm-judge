import asyncio
from dataclasses import replace

from kolas_llm_judge.binary_judge import (
    BinaryJudgeCall,
    BinaryJudgeConfig,
    MatchChecklistDecision,
    QualityChecklistDecision,
    SafetyChecklistDecision,
)
from kolas_llm_judge.qualification import (
    QualificationGateConfig,
    run_qualification,
)
from kolas_llm_judge.qualification_controls import load_generated_control_suite


class PerfectFakeJudge:
    def __init__(self) -> None:
        self.config = BinaryJudgeConfig(model="fake")
        self._expected = {
            control.control_id: control.expected
            for control in load_generated_control_suite().controls
        }

    async def evaluate_match_controls(self, controls):
        rows = []
        for control in controls:
            expected = self._expected[control.control_id]
            rows.append(
                MatchChecklistDecision(
                    id=control.control_id,
                    same_hazard_mechanism=expected.get("same_hazard_mechanism", True),
                    context_compatible=expected.get("context_compatible", True),
                    accident_compatible=expected.get("accident_compatible", True),
                )
            )
        return BinaryJudgeCall("match", rows, "m", "fake", {}, 1)

    async def evaluate_quality_controls(self, controls):
        rows = []
        for control in controls:
            expected = self._expected[control.control_id]
            rows.append(
                QualityChecklistDecision(
                    id=control.control_id,
                    mitigation_addresses_hazard=expected.get("mitigation_addresses_hazard", True),
                    mitigation_actionable=expected.get("mitigation_actionable", True),
                    mitigation_specific=expected.get("mitigation_specific", True),
                    unsafe_advice=expected.get("unsafe_advice", False),
                    legal_basis_relevant=expected.get("legal_basis_relevant", True),
                )
            )
        return BinaryJudgeCall("quality", rows, "q", "fake", {}, 1)

    async def evaluate_safety_controls(self, controls):
        rows = []
        for control in controls:
            expected = self._expected[control.control_id]
            rows.append(
                SafetyChecklistDecision(
                    id=control.control_id,
                    critical_safety_error=expected["critical_safety_error"],
                )
            )
        return BinaryJudgeCall("safety", rows, "s", "fake", {}, 1)


def gate_all_perfect() -> QualificationGateConfig:
    return QualificationGateConfig(
        gate_version="test",
        minimums={
            "structured_completion": 1.0,
            "match_identity_accuracy": 1.0,
            "match_negative_accuracy": 1.0,
            "accident_accuracy": 1.0,
            "mitigation_accuracy": 1.0,
            "legal_accuracy": 1.0,
            "critical_safety_accuracy": 1.0,
            "robustness_accuracy": 1.0,
            "repeated_decision_stability": 1.0,
        },
        required_families=[
            "match_identity",
            "match_negative",
            "accident",
            "mitigation",
            "legal",
            "critical_safety",
            "robustness",
        ],
    )


def test_perfect_qualification_passes_all_gates() -> None:
    result = asyncio.run(
        run_qualification(
            judge=PerfectFakeJudge(),
            gate=gate_all_perfect(),
            repeats=2,
        )
    )
    assert result.summary["gate_pass"] is True
    assert result.summary["control_count"] == 104
    assert result.summary["metrics"]["repeated_decision_stability"]["rate"] == 1.0
    assert all(check["pass"] for check in result.summary["checks"].values())


class OneWrongJudge(PerfectFakeJudge):
    async def evaluate_match_controls(self, controls):
        call = await super().evaluate_match_controls(controls)
        for row in call.rows:
            if row.id.endswith("match-identity"):
                row.same_hazard_mechanism = False
                break
        return call


def test_qualification_blocks_when_required_control_accuracy_fails() -> None:
    result = asyncio.run(
        run_qualification(
            judge=OneWrongJudge(),
            gate=gate_all_perfect(),
            repeats=2,
        )
    )
    assert result.summary["gate_pass"] is False
    assert result.summary["checks"]["match_identity_accuracy"]["pass"] is False
