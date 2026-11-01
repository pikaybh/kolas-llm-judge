"""Link each official run to a fresh, frozen, independent AJQG PASS."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import hashlib

from .io_utils import load_json
from .dataset import sha256_file


def validate_qualification_evidence(
    project_root: Path, *,
    expected_model: str,
    expected_effort: str,
    max_age_minutes: int = 120,
) -> tuple[dict[str, Any], Path]:
    base = project_root / "runs" / "_qualification"
    dirs = sorted(
        (folder for folder in base.iterdir()
         if folder.is_dir() and (folder / "summary.json").is_file()),
        key=lambda folder: (folder / "summary.json").stat().st_mtime,
        reverse=True,
    ) if base.exists() else []
    now = datetime.now(timezone.utc)
    for folder in dirs:
        summary_path = folder / "summary.json"
        details_path = folder / "control_results.csv"
        try:
            data = load_json(summary_path)
            if data.get("gate_pass") is not True or not details_path.is_file():
                continue
            if data.get("qualification_version") != "ajqg-v1":
                continue
            if data.get("control_count") != 104 or int(data.get("repeats", 0)) < 2:
                continue
            judge = data.get("judge") or {}
            if judge.get("model") != expected_model or judge.get("reasoning_effort") != expected_effort:
                continue
            finished = datetime.fromisoformat(data["completed_at_utc"].replace("Z", "+00:00"))
            age = now - finished.astimezone(timezone.utc)
            if not timedelta(0) <= age <= timedelta(minutes=max_age_minutes):
                continue
            # Bind to the exact frozen evaluator-side configuration files.
            config = data.get("frozen_evaluator") or {}
            if not config or not all(
                config.get(name) == sha256_file(project_root / rel)
                for name, rel in {
                    "prompt_sha256": "prompts/judge_binary_v1.md",
                    "rubric_sha256": "configs/rubric_binary_v1.yaml",
                    "gate_sha256": "configs/ajqg_gate_v1.yaml",
                    "seed_sha256": "configs/ajqg_seed_v1.yaml",
                }.items()
            ):
                continue
            # Each qualification is for one official run only.
            used = any(
                (run_dir / "manifest.json").is_file()
                and (load_json(run_dir / "manifest.json").get("qualification") or {}).get("summary_sha256") == sha256_file(summary_path)
                for run_dir in (project_root / "runs").iterdir() if run_dir.is_dir() and not run_dir.name.startswith("_")
            )
            if used:
                continue
            return {
                "mode": "independent-required-pass",
                "gate_pass": True,
                "summary_path": str(summary_path.relative_to(project_root)),
                "summary_sha256": sha256_file(summary_path),
                "controls_path": str(details_path.relative_to(project_root)),
                "controls_sha256": sha256_file(details_path),
                "completed_at_utc": data["completed_at_utc"],
                "control_count": 104,
                "repeats": data["repeats"],
                "judge": judge,
            }, summary_path
        except (ValueError, KeyError, TypeError, OSError):
            continue
    raise RuntimeError("AJQG_REQUIRED: run 'qualify-judge' and verify PASS within 120 minutes before every official run")
