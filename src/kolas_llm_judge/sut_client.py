from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, AsyncIterator
from urllib.parse import urlsplit, urlunsplit

import httpx

from .models import EvaluationScenario


RETRYABLE_STATUS_CODES = {
    408,
    425,
    429,
    500,
    502,
    503,
    504,
}


def _normalize_base_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parts = urlsplit(raw)
    path = parts.path.rstrip("/")
    if not path or path == "/":
        path = "/api"
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            path,
            "",
            "",
        )
    ).rstrip("/")


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
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5

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
                os.getenv(
                    "SEEXR_API_BASE_URL",
                    cls.base_url,
                )
            ),
            agent_id=os.getenv(
                "SEEXR_AGENT_ID",
                cls.agent_id,
            ),
            token=(
                os.getenv("SEEXR_API_TOKEN")
                or None
            ),
            email=(
                os.getenv("SEEXR_EMAIL")
                or None
            ),
            password=(
                os.getenv("SEEXR_PASSWORD")
                or None
            ),
            risk_assessment_method=os.getenv(
                "SEEXR_RISK_ASSESSMENT_METHOD",
                cls.risk_assessment_method,
            ),
            model_mode=os.getenv(
                "SEEXR_MODEL_MODE",
                cls.model_mode,
            ),
            reasoning_style=os.getenv(
                "SEEXR_REASONING_STYLE",
                cls.reasoning_style,
            ),
            timeout_seconds=float(
                os.getenv(
                    "SEEXR_TIMEOUT_SECONDS",
                    str(cls.timeout_seconds),
                )
            ),
            max_retries=max(
                0,
                int(
                    os.getenv(
                        "SEEXR_MAX_RETRIES",
                        str(cls.max_retries),
                    )
                ),
            ),
            retry_backoff_seconds=max(
                0.0,
                float(
                    os.getenv(
                        "SEEXR_RETRY_BACKOFF_SECONDS",
                        str(
                            cls.retry_backoff_seconds
                        ),
                    )
                ),
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
    create_run_attempts: int = 1
    stream_reconnects: int = 0
    retry_log: list[dict[str, Any]] = field(
        default_factory=list
    )
    auth_recoveries: int = 0


def build_sut_message(
    scenario: EvaluationScenario,
) -> str:
    p = scenario.input
    lines = [
        "다음 작업에 대해 위험성평가를 작성해주세요.",
        f"공정: {p.process}",
    ]
    if p.subprocess:
        lines.append(
            f"세부공정: {p.subprocess}"
        )
    if p.equipment:
        lines.append(
            "설비: "
            + ", ".join(p.equipment)
        )
    if p.materials:
        lines.append(
            "물질/자재: "
            + ", ".join(p.materials)
        )
    lines.append(
        "위에 명시되지 않은 설비·물질은 "
        "임의로 입력 사실로 간주하지 마세요."
    )
    return "\n".join(lines)


def _unwrap(payload: Any) -> Any:
    if (
        isinstance(payload, dict)
        and "data" in payload
    ):
        return payload["data"]
    return payload


def _event_fingerprint(
    event: dict[str, Any],
) -> str:
    return json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class SeexrSutClient:
    def __init__(
        self,
        config: SutConfig | None = None,
    ) -> None:
        self.config = (
            config or SutConfig.from_env()
        )
        headers = {
            "Accept": "application/json"
        }
        if self.config.token:
            headers[
                "Authorization"
            ] = (
                f"Bearer {self.config.token}"
            )
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=httpx.Timeout(
                self.config.timeout_seconds
            ),
        )
        self._static_token_mode = bool(self.config.token)
        self._refresh_token: str | None = None
        self._auth_recovery_count = 0
        self._auth_events: list[dict[str, Any]] = []
        self._auth_lock = asyncio.Lock()
        self._auth_version = 0

    async def __aenter__(
        self,
    ) -> "SeexrSutClient":
        return self

    async def __aexit__(
        self,
        *args: object,
    ) -> None:
        await self.client.aclose()

    def _backoff(
        self,
        retry_index: int,
    ) -> float:
        return min(
            5.0,
            (
                self.config.retry_backoff_seconds
                * (2 ** retry_index)
            ),
        )

    @staticmethod
    def _retryable_exception(
        exc: BaseException,
    ) -> bool:
        if isinstance(
            exc,
            (
                httpx.TimeoutException,
                httpx.TransportError,
            ),
        ):
            return True
        if isinstance(
            exc,
            httpx.HTTPStatusError,
        ):
            return (
                exc.response.status_code
                in RETRYABLE_STATUS_CODES
            )
        return False

    def _apply_auth_tokens(
        self,
        data: Any,
    ) -> None:
        data = _unwrap(data)
        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid SEEXR auth response"
            )
        tokens = data.get("tokens")
        if (
            not isinstance(tokens, dict)
            or not isinstance(
                tokens.get("accessToken"),
                str,
            )
        ):
            raise RuntimeError(
                "SEEXR auth response did not return an access token. "
                "Do not use an admin/MFA account for automated evaluation."
            )
        access_token = str(tokens["accessToken"])
        self.client.headers["Authorization"] = f"Bearer {access_token}"
        self._auth_version += 1
        refresh_token = tokens.get("refreshToken")
        if isinstance(refresh_token, str) and refresh_token:
            self._refresh_token = refresh_token
        self.config = replace(self.config, token=None)

    async def _login_with_password(
        self,
    ) -> None:
        if not self.config.email or not self.config.password:
            raise RuntimeError(
                "SEEXR email/password credentials are unavailable for login."
            )
        response = await self.client.post(
            "/auth/login",
            json={
                "email": self.config.email,
                "password": self.config.password,
            },
        )
        response.raise_for_status()
        self._apply_auth_tokens(response.json())

    async def _refresh_access_token(
        self,
    ) -> bool:
        if not self._refresh_token:
            return False
        response = await self.client.post(
            "/auth/refresh",
            json={"refreshToken": self._refresh_token},
        )
        if response.status_code >= 400:
            return False
        self._apply_auth_tokens(response.json())
        return True

    async def _recover_auth(
        self,
        *,
        reason: str = "401",
        observed_version: int | None = None,
    ) -> bool:
        if self._static_token_mode and not (
            self.config.email and self.config.password
        ):
            return False
        async with self._auth_lock:
            # Another concurrent request may already have refreshed the token
            # after this request was sent. In that case simply retry with the
            # newer Authorization header instead of rotating the refresh token
            # a second time.
            if (
                observed_version is not None
                and self._auth_version != observed_version
            ):
                return True

            action: str | None = None
            try:
                if await self._refresh_access_token():
                    action = "refresh"
                elif self.config.email and self.config.password:
                    await self._login_with_password()
                    action = "relogin"
            except Exception:
                if self.config.email and self.config.password:
                    try:
                        await self._login_with_password()
                        action = "relogin"
                    except Exception:
                        return False
                else:
                    return False
            if action is None:
                return False
            self._auth_recovery_count += 1
            self._auth_events.append(
                {
                    "stage": "auth",
                    "action": action,
                    "reason": reason,
                    "auth_version": self._auth_version,
                }
            )
            return True

    async def _request_with_auth_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        observed_version = self._auth_version
        response = await self.client.request(
            method,
            url,
            **kwargs,
        )
        if response.status_code == 401:
            recovered = await self._recover_auth(
                observed_version=observed_version
            )
            if recovered:
                response = await self.client.request(
                    method,
                    url,
                    **kwargs,
                )
        response.raise_for_status()
        return response

    async def ensure_authenticated(
        self,
    ) -> None:
        if self.config.token:
            return
        if (
            not self.config.email
            or not self.config.password
        ):
            raise RuntimeError(
                "SEEXR authentication is missing. "
                "Set SEEXR_API_TOKEN or "
                "SEEXR_EMAIL + SEEXR_PASSWORD "
                "for a non-admin evaluation account."
            )
        await self._login_with_password()

    async def healthcheck_auth(
        self,
    ) -> dict[str, Any]:
        response = await self._request_with_auth_retry(
            "GET",
            "/agents",
        )
        data = _unwrap(response.json())
        return (
            data
            if isinstance(data, dict)
            else {"data": data}
        )

    async def evaluation_account_state(
        self,
    ) -> dict[str, Any]:
        instruction_response = (
            await self._request_with_auth_retry(
                "GET",
                "/instructions/me",
            )
        )
        plan_response = (
            await self._request_with_auth_retry(
                "GET",
                "/users/me/plan",
            )
        )
        instruction = _unwrap(
            instruction_response.json()
        )
        plan = _unwrap(plan_response.json())

        content = (
            str(instruction.get("content") or "")
            if isinstance(instruction, dict)
            else ""
        )
        normalized_instruction = content.strip()
        usage = (
            plan.get("usage")
            if isinstance(plan, dict)
            else None
        )
        if not isinstance(usage, dict):
            usage = {}

        tokens_used = usage.get(
            "tokens_used_month"
        )
        tokens_limit = usage.get(
            "tokens_limit"
        )
        allowance_available = (
            tokens_limit is None
            or (
                isinstance(tokens_used, (int, float))
                and isinstance(tokens_limit, (int, float))
                and tokens_used < tokens_limit
            )
        )

        return {
            "saved_instruction_empty": (
                normalized_instruction == ""
            ),
            "saved_instruction_sha256": (
                hashlib.sha256(
                    normalized_instruction.encode(
                        "utf-8"
                    )
                ).hexdigest()
            ),
            "tokens_used_month": tokens_used,
            "tokens_limit": tokens_limit,
            "allowance_available": (
                allowance_available
            ),
        }

    async def create_session(
        self,
        case_id: str,
    ) -> str:
        response = await self._request_with_auth_retry(
            "POST",
            "/chat/sessions",
            json={
                "agentId": (
                    self.config.agent_id
                ),
                "surface": (
                    "risk_assessment_workspace"
                ),
                "title": f"KOLAS {case_id}",
            },
        )
        data = _unwrap(response.json())
        if (
            isinstance(data, dict)
            and isinstance(
                data.get("session"),
                dict,
            )
        ):
            data = data["session"]
        if (
            not isinstance(data, dict)
            or not data.get("id")
        ):
            raise RuntimeError(
                "Invalid session response: "
                f"{data!r}"
            )
        return str(data["id"])

    async def _create_run_once(
        self,
        scenario: EvaluationScenario,
        session_id: str,
        *,
        client_request_id: str,
    ) -> str:
        payload = {
            "message": (
                build_sut_message(scenario)
            ),
            "sessionId": session_id,
            "context": {
                "userLanguage": "ko",
                "modelMode": (
                    self.config.model_mode
                ),
                "protocol": "v2",
                "reasoningStyle": (
                    self.config.reasoning_style
                ),
                "riskAssessmentMethod": (
                    self.config
                    .risk_assessment_method
                ),
            },
            "clientRequestId": (
                client_request_id
            ),
        }
        response = await self._request_with_auth_retry(
            "POST",
            (
                f"/agents/"
                f"{self.config.agent_id}/runs"
            ),
            json=payload,
        )
        data = _unwrap(response.json())
        if (
            not isinstance(data, dict)
            or not data.get("runId")
        ):
            raise RuntimeError(
                "Invalid run response: "
                f"{data!r}"
            )
        return str(data["runId"])

    async def create_run(
        self,
        scenario: EvaluationScenario,
        session_id: str,
        *,
        client_request_id: str | None = None,
        retry_log: (
            list[dict[str, Any]] | None
        ) = None,
    ) -> tuple[str, int]:
        request_id = (
            client_request_id
            or str(uuid.uuid4())
        )
        log = (
            retry_log
            if retry_log is not None
            else []
        )
        total_attempts = (
            self.config.max_retries + 1
        )
        for attempt in range(
            1,
            total_attempts + 1,
        ):
            try:
                run_id = (
                    await self._create_run_once(
                        scenario,
                        session_id,
                        client_request_id=(
                            request_id
                        ),
                    )
                )
                return run_id, attempt
            except Exception as exc:
                retryable = (
                    self._retryable_exception(
                        exc
                    )
                )
                log.append(
                    {
                        "stage": "create_run",
                        "attempt": attempt,
                        "retryable": retryable,
                        "error_type": (
                            type(exc).__name__
                        ),
                        "status_code": (
                            exc.response.status_code
                            if isinstance(
                                exc,
                                httpx.HTTPStatusError,
                            )
                            else None
                        ),
                    }
                )
                if (
                    not retryable
                    or attempt
                    >= total_attempts
                ):
                    raise
                await asyncio.sleep(
                    self._backoff(
                        attempt - 1
                    )
                )
        raise RuntimeError(
            "create_run retry loop exhausted"
        )

    async def _iter_sse(
        self,
        run_id: str,
        *,
        after: int = 0,
    ) -> AsyncIterator[
        dict[str, Any]
    ]:
        auth_retried = False
        while True:
            observed_version = self._auth_version
            async with self.client.stream(
                "GET",
                (
                    f"/agents/runs/{run_id}/"
                    f"events?after={after}"
                ),
            ) as response:
                if (
                    response.status_code == 401
                    and not auth_retried
                ):
                    recovered = await self._recover_auth(
                        observed_version=observed_version
                    )
                    if recovered:
                        auth_retried = True
                        continue
                response.raise_for_status()
                async for line in (
                    response.aiter_lines()
                ):
                    if not line.startswith(
                        "data:"
                    ):
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
                return

    @staticmethod
    def _completed_content(
        event: dict[str, Any],
    ) -> str | None:
        content = event.get("content")
        if isinstance(content, str):
            return content
        payload = event.get("payload")
        if isinstance(payload, dict):
            nested = payload.get("content")
            if isinstance(nested, str):
                return nested
        return None

    async def run_case(
        self,
        scenario: EvaluationScenario,
        *,
        client_request_id: (
            str | None
        ) = None,
    ) -> SutRunResult:
        started = time.perf_counter()
        retry_log: list[
            dict[str, Any]
        ] = []
        auth_event_start = len(self._auth_events)

        session_id = (
            await self.create_session(
                scenario.case_id
            )
        )
        run_id, create_attempts = (
            await self.create_run(
                scenario,
                session_id,
                client_request_id=(
                    client_request_id
                ),
                retry_log=retry_log,
            )
        )

        events: list[
            dict[str, Any]
        ] = []
        seen_sequences: set[int] = set()
        seen_unsequenced: set[str] = set()
        last_sequence = 0
        reconnects = 0

        while True:
            terminal_seen = False
            try:
                async for event in (
                    self._iter_sse(
                        run_id,
                        after=last_sequence,
                    )
                ):
                    sequence_raw = (
                        event.get("sequence")
                    )
                    if isinstance(
                        sequence_raw,
                        int,
                    ):
                        if (
                            sequence_raw
                            in seen_sequences
                        ):
                            continue
                        seen_sequences.add(
                            sequence_raw
                        )
                        last_sequence = max(
                            last_sequence,
                            sequence_raw,
                        )
                    else:
                        fingerprint = (
                            _event_fingerprint(
                                event
                            )
                        )
                        if (
                            fingerprint
                            in seen_unsequenced
                        ):
                            continue
                        seen_unsequenced.add(
                            fingerprint
                        )

                    events.append(event)
                    event_type = (
                        event.get("type")
                    )
                    if (
                        event_type
                        == "run-completed"
                    ):
                        terminal_seen = True
                        content = (
                            self._completed_content(
                                event
                            )
                        )
                        if not isinstance(
                            content,
                            str,
                        ):
                            raise RuntimeError(
                                "run-completed event "
                                "has no final content"
                            )
                        return SutRunResult(
                            case_id=(
                                scenario.case_id
                            ),
                            session_id=(
                                session_id
                            ),
                            run_id=run_id,
                            content=content,
                            elapsed_ms=round(
                                (
                                    time.perf_counter()
                                    - started
                                )
                                * 1000
                            ),
                            events=events,
                            create_run_attempts=(
                                create_attempts
                            ),
                            stream_reconnects=(
                                reconnects
                            ),
                            retry_log=[
                                *retry_log,
                                *self._auth_events[auth_event_start:],
                            ],
                            auth_recoveries=len(
                                self._auth_events[auth_event_start:]
                            ),
                        )
                    if event_type in {
                        "run-failed",
                        "run-cancelled",
                    }:
                        terminal_seen = True
                        raise RuntimeError(
                            "SEEXR run terminated: "
                            f"{event}"
                        )

                if terminal_seen:
                    break

                exc = RuntimeError(
                    "SSE stream ended before "
                    "terminal event"
                )
                if (
                    reconnects
                    >= self.config.max_retries
                ):
                    raise exc
                reconnects += 1
                retry_log.append(
                    {
                        "stage": "sse",
                        "attempt": reconnects,
                        "retryable": True,
                        "error_type": (
                            "UnexpectedStreamEnd"
                        ),
                        "status_code": None,
                        "after_sequence": (
                            last_sequence
                        ),
                    }
                )
                await asyncio.sleep(
                    self._backoff(
                        reconnects - 1
                    )
                )
            except Exception as exc:
                # Explicit run-failed/cancelled and
                # schema errors must never reconnect.
                if (
                    isinstance(exc, RuntimeError)
                    and (
                        str(exc).startswith(
                            "SEEXR run terminated"
                        )
                        or "has no final content"
                        in str(exc)
                    )
                ):
                    raise

                retryable = (
                    self._retryable_exception(
                        exc
                    )
                )
                if (
                    not retryable
                    or reconnects
                    >= self.config.max_retries
                ):
                    raise
                reconnects += 1
                retry_log.append(
                    {
                        "stage": "sse",
                        "attempt": reconnects,
                        "retryable": True,
                        "error_type": (
                            type(exc).__name__
                        ),
                        "status_code": (
                            exc.response.status_code
                            if isinstance(
                                exc,
                                httpx.HTTPStatusError,
                            )
                            else None
                        ),
                        "after_sequence": (
                            last_sequence
                        ),
                    }
                )
                await asyncio.sleep(
                    self._backoff(
                        reconnects - 1
                    )
                )

        raise RuntimeError(
            "SSE stream ended before "
            "run-completed"
        )
