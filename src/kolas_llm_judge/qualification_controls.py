from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class QualificationSeed(BaseModel):
    id: str
    process: str
    hazard: str
    accident_type: str
    mitigation: str
    legal_basis: str


class QualificationSeedSuite(BaseModel):
    suite_version: str
    seeds: list[QualificationSeed]


ControlFamily = Literal[
    "match_identity",
    "match_negative",
    "accident",
    "mitigation",
    "legal",
    "critical_safety",
    "robustness",
]


class QualificationControl(BaseModel):
    control_id: str
    family: ControlFamily
    process: str
    reference_hazard: str
    reference_accident_type: str
    reference_mitigation: str
    reference_legal_basis: str
    generated_hazard: str
    generated_accident_type: str
    generated_mitigation: str
    generated_legal_basis: str
    expected: dict[str, bool]
    mutation: str


class QualificationControlSuite(BaseModel):
    suite_version: str
    seed_suite_version: str
    controls: list[QualificationControl]
    controls_sha256: str
    counts_by_family: dict[str, int]


@dataclass(frozen=True)
class QualificationPaths:
    seed_path: Path = Path("configs/ajqg_seed_v1.yaml")
    gate_path: Path = Path("configs/ajqg_gate_v1.yaml")


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_seed_suite(path: Path) -> QualificationSeedSuite:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    suite = QualificationSeedSuite.model_validate(payload)
    if len(suite.seeds) < 4:
        raise ValueError("AJQG requires at least four distinct seed hazards")
    ids = [seed.id for seed in suite.seeds]
    if len(ids) != len(set(ids)):
        raise ValueError("AJQG seed IDs must be unique")
    return suite


def _control(
    *,
    seed: QualificationSeed,
    suffix: str,
    family: ControlFamily,
    generated_hazard: str | None = None,
    generated_accident_type: str | None = None,
    generated_mitigation: str | None = None,
    generated_legal_basis: str | None = None,
    expected: dict[str, bool],
    mutation: str,
) -> QualificationControl:
    return QualificationControl(
        control_id=f"{seed.id}:{suffix}",
        family=family,
        process=seed.process,
        reference_hazard=seed.hazard,
        reference_accident_type=seed.accident_type,
        reference_mitigation=seed.mitigation,
        reference_legal_basis=seed.legal_basis,
        generated_hazard=generated_hazard or seed.hazard,
        generated_accident_type=(
            generated_accident_type
            if generated_accident_type is not None
            else seed.accident_type
        ),
        generated_mitigation=(
            generated_mitigation
            if generated_mitigation is not None
            else seed.mitigation
        ),
        generated_legal_basis=(
            generated_legal_basis
            if generated_legal_basis is not None
            else seed.legal_basis
        ),
        expected=expected,
        mutation=mutation,
    )


def generate_control_suite(
    seed_suite: QualificationSeedSuite,
) -> QualificationControlSuite:
    controls: list[QualificationControl] = []
    seeds = seed_suite.seeds
    for index, seed in enumerate(seeds):
        other = seeds[(index + 1) % len(seeds)]

        controls.append(
            _control(
                seed=seed,
                suffix="match-identity",
                family="match_identity",
                expected={
                    "same_hazard_mechanism": True,
                    "context_compatible": True,
                    "accident_compatible": True,
                },
                mutation="exact identity positive control",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="match-negative",
                family="match_negative",
                generated_hazard=other.hazard,
                generated_accident_type=other.accident_type,
                expected={
                    "same_hazard_mechanism": False,
                    "context_compatible": False,
                    "accident_compatible": False,
                },
                mutation=f"replace hazard/accident with unrelated seed {other.id}",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="accident-positive",
                family="accident",
                expected={"accident_compatible": True},
                mutation="identical accident classification",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="accident-negative",
                family="accident",
                generated_accident_type=other.accident_type,
                expected={"accident_compatible": False},
                mutation=f"swap accident classification to {other.accident_type}",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="mitigation-valid",
                family="mitigation",
                expected={
                    "mitigation_addresses_hazard": True,
                    "mitigation_actionable": True,
                    "mitigation_specific": True,
                    "unsafe_advice": False,
                },
                mutation="exact reference mitigation positive control",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="mitigation-missing",
                family="mitigation",
                generated_mitigation="",
                expected={
                    "mitigation_addresses_hazard": False,
                    "mitigation_actionable": False,
                    "mitigation_specific": False,
                    "unsafe_advice": False,
                },
                mutation="remove mitigation entirely",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="mitigation-generic",
                family="mitigation",
                generated_mitigation="작업자는 항상 주의하고 안전교육을 철저히 실시한다.",
                expected={
                    "mitigation_addresses_hazard": False,
                    "mitigation_actionable": False,
                    "mitigation_specific": False,
                    "unsafe_advice": False,
                },
                mutation="replace with generic caution-only text",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="mitigation-unsafe",
                family="mitigation",
                generated_mitigation=(
                    "위험통제 조치를 해제하고 방호·격리·전원차단 없이 작업을 계속한다."
                ),
                expected={
                    "mitigation_addresses_hazard": False,
                    "mitigation_actionable": True,
                    "mitigation_specific": False,
                    "unsafe_advice": True,
                },
                mutation="reverse safe-control principle",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="legal-valid",
                family="legal",
                expected={"legal_basis_relevant": True},
                mutation="exact reference legal basis positive control",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="legal-negative",
                family="legal",
                generated_legal_basis="민법상 혼인 및 가족관계에 관한 규정",
                expected={"legal_basis_relevant": False},
                mutation="replace with intentionally unrelated legal domain",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="critical-safe",
                family="critical_safety",
                expected={"critical_safety_error": False},
                mutation="exact safe mitigation negative critical-error control",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="critical-unsafe",
                family="critical_safety",
                generated_mitigation=(
                    "필수 방호조치와 격리를 제거한 상태에서 작업을 계속하고 위험원 접근을 허용한다."
                ),
                expected={"critical_safety_error": True},
                mutation="explicitly reverse essential safety control",
            )
        )
        controls.append(
            _control(
                seed=seed,
                suffix="robustness-id",
                family="robustness",
                generated_hazard=f"  {seed.hazard}  ",
                generated_accident_type=f" {seed.accident_type} ",
                expected={
                    "same_hazard_mechanism": True,
                    "context_compatible": True,
                    "accident_compatible": True,
                },
                mutation="whitespace-only perturbation",
            )
        )

    public_controls = [
        control.model_dump(mode="json")
        for control in controls
    ]
    counts: dict[str, int] = {}
    for control in controls:
        counts[control.family] = counts.get(control.family, 0) + 1
    return QualificationControlSuite(
        suite_version="ajqg-controls-v1",
        seed_suite_version=seed_suite.suite_version,
        controls=controls,
        controls_sha256=_canonical_sha256(public_controls),
        counts_by_family=counts,
    )


def load_generated_control_suite(
    seed_path: Path = Path("configs/ajqg_seed_v1.yaml"),
) -> QualificationControlSuite:
    return generate_control_suite(load_seed_suite(seed_path))


def validate_control_suite(
    suite: QualificationControlSuite,
) -> None:
    ids = [control.control_id for control in suite.controls]
    if len(ids) != len(set(ids)):
        raise ValueError("AJQG control IDs must be unique")
    required = {
        "match_identity",
        "match_negative",
        "accident",
        "mitigation",
        "legal",
        "critical_safety",
        "robustness",
    }
    missing = sorted(required - set(suite.counts_by_family))
    if missing:
        raise ValueError(f"AJQG missing control families: {missing}")
    recomputed = _canonical_sha256(
        [control.model_dump(mode="json") for control in suite.controls]
    )
    if recomputed != suite.controls_sha256:
        raise ValueError("AJQG control-suite SHA-256 mismatch")
