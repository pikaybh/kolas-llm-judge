from __future__ import annotations

import asyncio
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from .binary_judge import (
    BinaryChecklistJudge,
    BinaryJudgeCall,
)
from .io_utils import atomic_write_json
from .qualification_controls import (
    QualificationControl,
    QualificationControlSuite,
    load_generated_control_suite,
    validate_control_suite,
)


class QualificationGateConfig(BaseModel):
    gate_version: str
    minimums: dict[str, float]
    required_families: list[str]


@dataclass
class QualificationRunResult:
    summary: dict[str, Any]
    control_rows: list[dict[str, Any]]
    calls: list[dict[str, Any]]


def load_gate_config(path: Path = Path("configs/ajqg_gate_v1.yaml")) -> QualificationGateConfig:
    return QualificationGateConfig.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def _call_metadata(call: BinaryJudgeCall, repeat: int) -> dict[str, Any]:
    return {
        "repeat": repeat,
        "stage": call.stage,
        "elapsed_ms": call.elapsed_ms,
        "response_id": call.response_id,
        "response_model": call.response_model,
        "usage": call.usage,
        "row_count": len(call.rows),
    }


def _decision_dict(row: Any) -> dict[str, bool]:
    payload = row.model_dump(mode="json")
    payload.pop("id", None)
    return {
        key: bool(value)
        for key, value in payload.items()
        if isinstance(value, bool)
    }


def _stage_controls(
    suite: QualificationControlSuite,
) -> tuple[
    list[QualificationControl],
    list[QualificationControl],
    list[QualificationControl],
]:
    match_families = {
        "match_identity",
        "match_negative",
        "accident",
        "robustness",
    }
    quality_families = {"mitigation", "legal"}
    safety_families = {"critical_safety"}
    return (
        [x for x in suite.controls if x.family in match_families],
        [x for x in suite.controls if x.family in quality_families],
        [x for x in suite.controls if x.family in safety_families],
    )


async def _evaluate_once(
    judge: BinaryChecklistJudge,
    suite: QualificationControlSuite,
    *,
    repeat: int,
) -> tuple[dict[str, dict[str, bool]], list[dict[str, Any]]]:
    match_controls, quality_controls, safety_controls = _stage_controls(suite)
    match_call, quality_call, safety_call = await asyncio.gather(
        judge.evaluate_match_controls(match_controls),
        judge.evaluate_quality_controls(quality_controls),
        judge.evaluate_safety_controls(safety_controls),
    )

    outputs: dict[str, dict[str, bool]] = {}
    for call in (match_call, quality_call, safety_call):
        for row in call.rows:
            outputs[str(row.id)] = _decision_dict(row)
    return outputs, [
        _call_metadata(match_call, repeat),
        _call_metadata(quality_call, repeat),
        _call_metadata(safety_call, repeat),
    ]


def _accuracy(
    controls: list[QualificationControl],
    outputs: dict[str, dict[str, bool]],
) -> tuple[int, int, float | None, list[dict[str, Any]]]:
    correct = 0
    total = 0
    rows: list[dict[str, Any]] = []
    for control in controls:
        actual = outputs.get(control.control_id, {})
        for dimension, expected in control.expected.items():
            value = actual.get(dimension)
            ok = value is expected
            total += 1
            correct += int(ok)
            rows.append(
                {
                    "control_id": control.control_id,
                    "family": control.family,
                    "dimension": dimension,
                    "expected": expected,
                    "actual": value,
                    "correct": ok,
                    "mutation": control.mutation,
                }
            )
    return correct, total, (correct / total if total else None), rows


def _repeatability(
    first: dict[str, dict[str, bool]],
    second: dict[str, dict[str, bool]],
) -> tuple[int, int, float | None]:
    same = 0
    total = 0
    for control_id in sorted(set(first) & set(second)):
        first_decisions = first[control_id]
        second_decisions = second[control_id]
        for dimension in sorted(set(first_decisions) & set(second_decisions)):
            total += 1
            same += int(
                first_decisions[dimension]
                == second_decisions[dimension]
            )
    return same, total, (same / total if total else None)


def _family_metric_name(family: str) -> str:
    return {
        "match_identity": "match_identity_accuracy",
        "match_negative": "match_negative_accuracy",
        "accident": "accident_accuracy",
        "mitigation": "mitigation_accuracy",
        "legal": "legal_accuracy",
        "critical_safety": "critical_safety_accuracy",
        "robustness": "robustness_accuracy",
    }[family]


async def run_qualification(
    *,
    judge: BinaryChecklistJudge | None = None,
    suite: QualificationControlSuite | None = None,
    gate: QualificationGateConfig | None = None,
    repeats: int = 2,
) -> QualificationRunResult:
    if repeats < 2:
        raise ValueError("AJQG requires at least two repeats for stability measurement")
    suite = suite or load_generated_control_suite()
    validate_control_suite(suite)
    gate = gate or load_gate_config()
    judge = judge or BinaryChecklistJudge()

    repeat_outputs: list[dict[str, dict[str, bool]]] = []
    calls: list[dict[str, Any]] = []
    structured_successes = 0
    structured_expected = repeats * 3
    for repeat in range(1, repeats + 1):
        outputs, repeat_calls = await _evaluate_once(
            judge,
            suite,
            repeat=repeat,
        )
        repeat_outputs.append(outputs)
        calls.extend(repeat_calls)
        structured_successes += len(repeat_calls)

    primary_outputs = repeat_outputs[0]
    controls_by_family: dict[str, list[QualificationControl]] = defaultdict(list)
    for control in suite.controls:
        controls_by_family[control.family].append(control)

    metrics: dict[str, dict[str, Any]] = {}
    control_rows: list[dict[str, Any]] = []
    for family, controls in sorted(controls_by_family.items()):
        correct, total, rate, rows = _accuracy(controls, primary_outputs)
        metric_name = _family_metric_name(family)
        metrics[metric_name] = {
            "correct": correct,
            "total": total,
            "rate": rate,
        }
        control_rows.extend(rows)

    structured_rate = structured_successes / structured_expected
    metrics["structured_completion"] = {
        "correct": structured_successes,
        "total": structured_expected,
        "rate": structured_rate,
    }

    pairwise_stabilities: list[float] = []
    repeatability_detail: list[dict[str, Any]] = []
    for index in range(1, len(repeat_outputs)):
        same, total, rate = _repeatability(repeat_outputs[0], repeat_outputs[index])
        if rate is not None:
            pairwise_stabilities.append(rate)
        repeatability_detail.append(
            {
                "baseline_repeat": 1,
                "comparison_repeat": index + 1,
                "same": same,
                "total": total,
                "rate": rate,
            }
        )
    stability = min(pairwise_stabilities) if pairwise_stabilities else None
    metrics["repeated_decision_stability"] = {
        "rate": stability,
        "comparisons": repeatability_detail,
    }

    checks: dict[str, dict[str, Any]] = {}
    for metric_name, minimum in gate.minimums.items():
        rate = metrics.get(metric_name, {}).get("rate")
        checks[metric_name] = {
            "value": rate,
            "minimum": minimum,
            "pass": rate is not None and rate >= minimum,
        }

    family_presence = set(controls_by_family)
    missing_families = sorted(set(gate.required_families) - family_presence)
    checks["required_families"] = {
        "value": sorted(family_presence),
        "required": gate.required_families,
        "missing": missing_families,
        "pass": not missing_families,
    }

    summary = {
        "qualification_version": "ajqg-v1",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "gate_version": gate.gate_version,
        "control_suite_version": suite.suite_version,
        "control_suite_sha256": suite.controls_sha256,
        "control_count": len(suite.controls),
        "counts_by_family": suite.counts_by_family,
        "judge": {
            "pipeline_version": judge.config.pipeline_version,
            "model": judge.config.model,
            "reasoning_effort": judge.config.reasoning_effort,
            "max_concurrency": judge.config.max_concurrency,
            "prompt_path": str(judge.config.prompt_path),
            "rubric_path": str(judge.config.rubric_path),
        },
        "repeats": repeats,
        "metrics": metrics,
        "checks": checks,
        "gate_pass": all(check["pass"] for check in checks.values()),
        "calls": calls,
    }
    return QualificationRunResult(
        summary=summary,
        control_rows=control_rows,
        calls=calls,
    )


def write_qualification_artifacts(
    result: QualificationRunResult,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    controls_path = output_dir / "control_results.csv"
    atomic_write_json(summary_path, result.summary)
    fields = [
        "control_id",
        "family",
        "dimension",
        "expected",
        "actual",
        "correct",
        "mutation",
    ]
    with controls_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result.control_rows)
    return {
        "summary": summary_path,
        "controls": controls_path,
    }
