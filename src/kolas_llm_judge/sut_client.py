from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, replace
from typing import Any, AsyncIterator
from urllib.parse import urlsplit, urlunsplit

import httpx

from .models import EvaluationScenario


def _normalize_base_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parts = urlsplit(raw)
    path = parts.path.rstrip("/")
    if not path or path == "/":
        path = "/api"
    return urlunsplit((parts.scheme, parts.netloc, path, "", "")).rstrip("/")


@dataclass(frozen=True)
class SutConfig:
    base_url: str = "https://api.seexr.dev/api"
    agent_id: str = "risk-assessment"
    token: str | None = None
    email: str | None = None
    password: str | None = None
    risk_assessment_method: str = "빈도강도법 5x4"
    model_mode: str = "fast"
    reasoning_style: str = "balanced"
    timeout_seconds: float = 180.0

    @property
    def auth_mode(self) -> str:
        if self.token:
            return "token"
        if self.email and self.password:
            return "email_password"
        return "missing"

    @classmethod
    def from_env(cls) -> "SutConfig":
        return cls(
            base_url=_normalize_base_url(
                os.getenv("SEEXR_API_BASE_URL", cls.base_url)
            ),
            agent_id=os.getenv("SEEXR_AGENT_ID", cls.agent_id),
            token=os.getenv("SEEXR_API_TOKEN") or None,
            email=os.getenv("SEEXR_EMAIL") or None,
            password=os.getenv("SEEXR_PASSWORD") or None,
            risk_assessment_method=os.getenv(
                "SEEXR_RISK_ASSESSMENT_METHOD",
                cls.risk_assessment_method,
            ),
            model_mode=os.getenv("SEEXR_MODEL_MODE", cls.model_mode),
            reasoning_style=os.getenv(
                "SEEXR_REASONING_STYLE",
                cls.reasoning_style,
            ),
            timeout_seconds=float(
                os.getenv("SEEXR_TIMEOUT_SECONDS", str(cls.timeout_seconds))
            ),
        )


@dataclass
class SutRunResult:
    case_id: str
    session_id: str
    run_id: str
    content: str
    elapsed_ms: int
    events: list[dict[str, Any]]


def build_sut_message(scenario: EvaluationScenario) -> str:
    p = scenario.input
    lines = [
        "다음 작업에 대해 위험성평가를 작성해주세요.",
        f"공정: {p.process}",
    ]
    if p.subprocess:
        lines.append(f"세부공정: {p.subprocess}")
    if p.equipment:
        lines.append("설비: " + ", ".join(p.equipment))
    if p.materials:
        lines.append("물질/자재: " + ", ".join(p.materials))
    lines.append(
        "위에 명시되지 않은 설비·물질은 임의로 입력 사실로 간주하지 마세요."
    )
    return "\n".join(lines)


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


class SeexrSutClient:
    def __init__(self, config: SutConfig | None = None) -> None:
        self.config = config or SutConfig.from_env()
        headers = {"Accept": "application/json"}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=httpx.Timeout(self.config.timeout_seconds),
        )

    async def __aenter__(self) -> "SeexrSutClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.client.aclose()

    async def ensure_authenticated(self) -> None:
        if self.config.token:
            return
        if not self.config.email or not self.config.password:
            raise RuntimeError(
                "SEEXR authentication is missing. Set SEEXR_API_TOKEN or "
                "SEEXR_EMAIL + SEEXR_PASSWORD for a non-admin evaluation account."
            )
        response = await self.client.post(
            "/auth/login",
            json={
                "email": self.config.email,
                "password": self.config.password,
            },
        )
        response.raise_for_status()
        data = _unwrap(response.json())
        if not isinstance(data, dict):
            raise RuntimeError("Invalid SEEXR login response")
        tokens = data.get("tokens")
        if not isinstance(tokens, dict) or not isinstance(
            tokens.get("accessToken"), str
        ):
            raise RuntimeError(
                "SEEXR login did not return an access token. "
                "Do not use an admin/MFA account for automated evaluation."
            )
        token = str(tokens["accessToken"])
        self.client.headers["Authorization"] = f"Bearer {token}"
        # Preserve config metadata without ever persisting the acquired token.
        self.config = replace(self.config, token=None)

    async def healthcheck_auth(self) -> dict[str, Any]:
        response = await self.client.get("/agents")
        response.raise_for_status()
        data = _unwrap(response.json())
        return data if isinstance(data, dict) else {"data": data}

    async def create_session(self, case_id: str) -> str:
        response = await self.client.post(
            "/chat/sessions",
            json={
                "agentId": self.config.agent_id,
                "surface": "risk_assessment_workspace",
                "title": f"KOLAS {case_id}",
            },
        )
        response.raise_for_status()
        data = _unwrap(response.json())
        if isinstance(data, dict) and isinstance(data.get("session"), dict):
            data = data["session"]
        if not isinstance(data, dict) or not data.get("id"):
            raise RuntimeError(f"Invalid session response: {data!r}")
        return str(data["id"])

    async def create_run(
        self,
        scenario: EvaluationScenario,
        session_id: str,
        *,
        client_request_id: str | None = None,
    ) -> str:
        payload = {
            "message": build_sut_message(scenario),
            "sessionId": session_id,
            "context": {
                "userLanguage": "ko",
                "modelMode": self.config.model_mode,
                "protocol": "v2",
                "reasoningStyle": self.config.reasoning_style,
                "riskAssessmentMethod": self.config.risk_assessment_method,
            },
            "clientRequestId": client_request_id or str(uuid.uuid4()),
        }
        response = await self.client.post(
            f"/agents/{self.config.agent_id}/runs",
            json=payload,
        )
        response.raise_for_status()
        data = _unwrap(response.json())
        if not isinstance(data, dict) or not data.get("runId"):
            raise RuntimeError(f"Invalid run response: {data!r}")
        return str(data["runId"])

    async def _iter_sse(
        self,
        run_id: str,
        *,
        after: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        async with self.client.stream(
            "GET",
            f"/agents/runs/{run_id}/events?after={after}",
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    yield event

    async def run_case(
        self,
        scenario: EvaluationScenario,
        *,
        client_request_id: str | None = None,
    ) -> SutRunResult:
        started = time.perf_counter()
        session_id = await self.create_session(scenario.case_id)
        run_id = await self.create_run(
            scenario,
            session_id,
            client_request_id=client_request_id,
        )
        events: list[dict[str, Any]] = []
        async for event in self._iter_sse(run_id):
            events.append(event)
            event_type = event.get("type")
            if event_type == "run-completed":
                content = event.get("content")
                if not isinstance(content, str):
                    # Compatibility with any older nested event envelope.
                    payload = (
                        event.get("payload")
                        if isinstance(event.get("payload"), dict)
                        else {}
                    )
                    content = payload.get("content")
                if not isinstance(content, str):
                    raise RuntimeError(
                        "run-completed event has no final content"
                    )
                return SutRunResult(
                    case_id=scenario.case_id,
                    session_id=session_id,
                    run_id=run_id,
                    content=content,
                    elapsed_ms=round(
                        (time.perf_counter() - started) * 1000
                    ),
                    events=events,
                )
            if event_type in {"run-failed", "run-cancelled"}:
                raise RuntimeError(f"SEEXR run terminated: {event}")
        raise RuntimeError("SSE stream ended before run-completed")
