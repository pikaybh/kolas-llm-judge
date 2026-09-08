from __future__ import annotations

import asyncio

import httpx

from kolas_llm_judge.models import (
    EvaluationScenario,
    ScenarioInput,
)
from kolas_llm_judge.sut_client import (
    SeexrSutClient,
    SutConfig,
)


class RetryCreateRunClient(SeexrSutClient):
    def __init__(self) -> None:
        super().__init__(
            SutConfig(
                token="x",
                max_retries=2,
                retry_backoff_seconds=0,
            )
        )
        self.request_ids: list[str] = []

    async def _create_run_once(
        self,
        scenario,
        session_id,
        *,
        client_request_id,
    ):
        self.request_ids.append(
            client_request_id
        )
        if len(self.request_ids) == 1:
            request = httpx.Request(
                "POST",
                "https://example.test",
            )
            raise httpx.ConnectError(
                "temporary",
                request=request,
            )
        return "run-ok"


def test_create_run_retry_reuses_client_request_id() -> None:
    client = RetryCreateRunClient()
    scenario = EvaluationScenario(
        case_id="c",
        source_rows=[2],
        input=ScenarioInput(process="p"),
        references=[],
    )
    retry_log: list[dict] = []
    run_id, attempts = asyncio.run(
        client.create_run(
            scenario,
            "session",
            client_request_id="stable-id",
            retry_log=retry_log,
        )
    )
    asyncio.run(client.client.aclose())

    assert run_id == "run-ok"
    assert attempts == 2
    assert client.request_ids == [
        "stable-id",
        "stable-id",
    ]
    assert retry_log[0]["stage"] == "create_run"
    assert (
        retry_log[0]["retryable"]
        is True
    )


class ReconnectClient(SeexrSutClient):
    def __init__(self) -> None:
        super().__init__(
            SutConfig(
                token="x",
                max_retries=2,
                retry_backoff_seconds=0,
            )
        )
        self.stream_calls: list[int] = []

    async def create_session(
        self,
        case_id: str,
    ) -> str:
        return "session"

    async def create_run(
        self,
        scenario,
        session_id,
        *,
        client_request_id=None,
        retry_log=None,
    ):
        return "run", 1

    async def _iter_sse(
        self,
        run_id: str,
        *,
        after: int = 0,
    ):
        self.stream_calls.append(after)
        if len(self.stream_calls) == 1:
            yield {
                "sequence": 1,
                "type": "agent-message",
                "content": "partial",
            }
            request = httpx.Request(
                "GET",
                "https://example.test",
            )
            raise httpx.ReadError(
                "cut",
                request=request,
            )
        yield {
            "sequence": 1,
            "type": "agent-message",
            "content": "duplicate",
        }
        yield {
            "sequence": 2,
            "type": "run-completed",
            "content": "<risk_assessment/>",
        }


def test_sse_reconnect_resumes_and_dedupes() -> None:
    client = ReconnectClient()
    scenario = EvaluationScenario(
        case_id="c",
        source_rows=[2],
        input=ScenarioInput(process="p"),
        references=[],
    )
    result = asyncio.run(
        client.run_case(
            scenario,
            client_request_id="stable",
        )
    )
    asyncio.run(client.client.aclose())

    assert client.stream_calls == [0, 1]
    assert result.stream_reconnects == 1
    assert [
        event.get("sequence")
        for event in result.events
    ] == [1, 2]
    assert result.retry_log[0]["stage"] == "sse"
    assert (
        result.retry_log[0][
            "after_sequence"
        ]
        == 1
    )
