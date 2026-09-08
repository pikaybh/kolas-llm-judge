from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .dataset import sha256_file
from .io_utils import load_json, load_scenarios
from .judge import JudgeConfig
from .manifest import capture_sut_source_fingerprints
from .sut_client import SeexrSutClient, SutConfig


def _git(
    project_root: Path,
    *args: str,
) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=project_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


async def run_doctor(
    *,
    project_root: Path,
    scenarios_path: Path,
    live: bool = False,
    official: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def add(
        name: str,
        ok: bool,
        detail: str,
    ) -> None:
        checks.append(
            {
                "name": name,
                "ok": ok,
                "detail": detail,
            }
        )

    def warn(
        name: str,
        detail: str,
    ) -> None:
        warnings.append(
            {
                "name": name,
                "detail": detail,
            }
        )

    add(
        "project_root",
        project_root.exists(),
        str(project_root),
    )
    add(
        "scenarios_file",
        scenarios_path.exists(),
        str(scenarios_path),
    )

    if scenarios_path.exists():
        try:
            scenarios = load_scenarios(
                scenarios_path
            )
            add(
                "scenario_count",
                len(scenarios) == 425,
                (
                    f"{len(scenarios)} scenarios "
                    "(expected 425)"
                ),
            )
        except Exception as exc:
            add(
                "scenario_parse",
                False,
                str(exc),
            )

    dataset_manifest = (
        project_root
        / "data/cases/dataset_manifest.json"
    )
    if (
        dataset_manifest.exists()
        and scenarios_path.exists()
    ):
        manifest = load_json(
            dataset_manifest
        )
        actual = sha256_file(
            scenarios_path
        )
        add(
            "scenario_sha256",
            (
                manifest.get("cases_sha256")
                == actual
            ),
            f"actual={actual}",
        )
        add(
            "reference_count",
            (
                manifest.get(
                    "reference_count"
                )
                == 843
            ),
            (
                "reference_count="
                f"{manifest.get('reference_count')}"
            ),
        )
    else:
        add(
            "dataset_manifest",
            False,
            "dataset manifest not found",
        )

    required_files = [
        project_root
        / "configs/evaluation.yaml",
        project_root
        / "configs/rubric_v1.yaml",
        project_root
        / "prompts/judge_v1.md",
        project_root
        / "docs/evaluation_spec.md",
        project_root
        / "data/raw/PROVENANCE.md",
        project_root / "uv.lock",
    ]
    for path in required_files:
        add(
            f"file:{path.name}",
            path.exists(),
            str(path),
        )

    git_head = _git(
        project_root,
        "rev-parse",
        "HEAD",
    )
    git_status = _git(
        project_root,
        "status",
        "--porcelain",
    )
    if official:
        add(
            "evaluation_git_head",
            bool(git_head),
            git_head or "no git commit",
        )
        add(
            "evaluation_worktree_clean",
            (
                git_status is not None
                and git_status == ""
            ),
            (
                "clean"
                if git_status == ""
                else "uncommitted changes present"
            ),
        )
    elif not git_head:
        warn(
            "evaluation_git_head",
            "No evaluation harness commit yet.",
        )

    sut_source = (
        capture_sut_source_fingerprints()
    )
    for component in ("core", "agents"):
        row = sut_source.get(component, {})
        add(
            f"sut_source:{component}",
            bool(row.get("available")),
            (
                "relevant_files="
                f"{row.get('relevant_file_count')}, "
                "relevant_dirty="
                f"{row.get('relevant_dirty')}, "
                "hash="
                f"{row.get('relevant_source_fingerprint_sha256')}"
            ),
        )
        if row.get("relevant_dirty"):
            warn(
                f"sut_source:{component}:dirty",
                (
                    "Relevant production source has "
                    "uncommitted changes. Exact content "
                    "hash will still be frozen in each "
                    "run manifest."
                ),
            )

    sut_config = SutConfig.from_env()
    judge_config = JudgeConfig.from_env()
    add(
        "seexr_credentials",
        sut_config.auth_mode != "missing",
        f"auth_mode={sut_config.auth_mode}",
    )
    if official:
        renewable = sut_config.auth_mode == "email_password"
        add(
            "seexr_renewable_auth",
            renewable,
            (
                "email_password with refresh/relogin support"
                if renewable
                else "official long run requires SEEXR_EMAIL + SEEXR_PASSWORD; static access tokens cannot be renewed"
            ),
        )
    elif sut_config.auth_mode == "token":
        warn(
            "seexr_static_token",
            "SEEXR_API_TOKEN is suitable only if it remains valid for the whole run; email/password supports automatic refresh.",
        )
    add(
        "openai_credentials",
        bool(os.getenv("OPENAI_API_KEY")),
        (
            "OPENAI_API_KEY present"
            if os.getenv("OPENAI_API_KEY")
            else "OPENAI_API_KEY missing"
        ),
    )
    add(
        "judge_model",
        bool(judge_config.model),
        judge_config.model,
    )
    add(
        "judge_max_pairs_per_call",
        (
            judge_config.max_pairs_per_call
            > 0
        ),
        str(
            judge_config.max_pairs_per_call
        ),
    )
    add(
        "seexr_max_retries",
        sut_config.max_retries >= 0,
        str(sut_config.max_retries),
    )

    if (
        live
        and sut_config.auth_mode
        != "missing"
    ):
        try:
            async with SeexrSutClient(
                sut_config
            ) as sut:
                await sut.ensure_authenticated()
                data = (
                    await sut.healthcheck_auth()
                )
                agents = (
                    data.get("agents")
                    if isinstance(data, dict)
                    else None
                )
                risk_available = (
                    isinstance(agents, list)
                    and any(
                        isinstance(
                            agent,
                            dict,
                        )
                        and agent.get("id")
                        == sut_config.agent_id
                        and agent.get(
                            "enabled",
                            True,
                        )
                        for agent in agents
                    )
                )
                add(
                    "seexr_live_auth",
                    True,
                    (
                        "authenticated API "
                        "request succeeded"
                    ),
                )
                add(
                    "risk_agent_available",
                    risk_available,
                    sut_config.agent_id,
                )
        except Exception as exc:
            add(
                "seexr_live_auth",
                False,
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

    return {
        "ok": all(
            check["ok"]
            for check in checks
        ),
        "live_checked": live,
        "official_checked": official,
        "checks": checks,
        "warnings": warnings,
    }
