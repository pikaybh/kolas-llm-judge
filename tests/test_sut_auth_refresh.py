from __future__ import annotations

import asyncio
import json

import httpx

from kolas_llm_judge.sut_client import (
    SeexrSutClient,
    SutConfig,
)


def _auth_payload(
    access: str,
    refresh: str,
) -> dict:
    return {
        "data": {
            "tokens": {
                "accessToken": access,
                "refreshToken": refresh,
            }
        }
    }


def test_401_refreshes_rotating_token_and_retries_session() -> None:
    state = {
        "session_calls": 0,
        "refresh_calls": 0,
    }

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            return httpx.Response(
                200,
                json=_auth_payload(
                    "access-1",
                    "refresh-1",
                ),
            )
        if path.endswith("/auth/refresh"):
            state["refresh_calls"] += 1
            body = json.loads(
                request.content.decode()
            )
            assert (
                body["refreshToken"]
                == "refresh-1"
            )
            return httpx.Response(
                200,
                json=_auth_payload(
                    "access-2",
                    "refresh-2",
                ),
            )
        if path.endswith("/chat/sessions"):
            state["session_calls"] += 1
            authorization = (
                request.headers.get(
                    "Authorization"
                )
            )
            if (
                state["session_calls"]
                == 1
            ):
                assert (
                    authorization
                    == "Bearer access-1"
                )
                return httpx.Response(
                    401,
                    json={
                        "message": "expired"
                    },
                )
            assert (
                authorization
                == "Bearer access-2"
            )
            return httpx.Response(
                201,
                json={
                    "data": {
                        "id": "session-public"
                    }
                },
            )
        raise AssertionError(path)

    client = SeexrSutClient(
        SutConfig(
            base_url=(
                "https://example.test/api"
            ),
            email="eval@example.test",
            password="password",
        )
    )
    asyncio.run(
        client.client.aclose()
    )
    client.client = httpx.AsyncClient(
        base_url=client.config.base_url,
        transport=httpx.MockTransport(
            handler
        ),
        headers={
            "Accept": "application/json"
        },
    )

    asyncio.run(
        client.ensure_authenticated()
    )
    session_id = asyncio.run(
        client.create_session("case-1")
    )
    asyncio.run(
        client.client.aclose()
    )

    assert session_id == "session-public"
    assert state["refresh_calls"] == 1
    assert state["session_calls"] == 2
    assert (
        client._refresh_token
        == "refresh-2"
    )
    assert (
        client._auth_recovery_count
        == 1
    )
    assert client._auth_events == [
        {
            "stage": "auth",
            "action": "refresh",
            "reason": "401",
        }
    ]


def test_sse_401_refreshes_before_streaming_events() -> None:
    state = {
        "event_calls": 0,
    }

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            return httpx.Response(
                200,
                json=_auth_payload(
                    "access-1",
                    "refresh-1",
                ),
            )
        if path.endswith("/auth/refresh"):
            return httpx.Response(
                200,
                json=_auth_payload(
                    "access-2",
                    "refresh-2",
                ),
            )
        if "/events" in path:
            state["event_calls"] += 1
            if state["event_calls"] == 1:
                return httpx.Response(
                    401,
                    json={
                        "message": "expired"
                    },
                )
            assert (
                request.headers.get(
                    "Authorization"
                )
                == "Bearer access-2"
            )
            return httpx.Response(
                200,
                headers={
                    "content-type": (
                        "text/event-stream"
                    )
                },
                content=(
                    'data: {"sequence":1,'
                    '"type":"run-completed",'
                    '"content":"done"}\n\n'
                ),
            )
        raise AssertionError(path)

    client = SeexrSutClient(
        SutConfig(
            base_url=(
                "https://example.test/api"
            ),
            email="eval@example.test",
            password="password",
        )
    )
    asyncio.run(
        client.client.aclose()
    )
    client.client = httpx.AsyncClient(
        base_url=client.config.base_url,
        transport=httpx.MockTransport(
            handler
        ),
        headers={
            "Accept": "application/json"
        },
    )
    asyncio.run(
        client.ensure_authenticated()
    )

    async def collect() -> list[dict]:
        return [
            event
            async for event
            in client._iter_sse(
                "run-1",
                after=0,
            )
        ]

    events = asyncio.run(collect())
    asyncio.run(
        client.client.aclose()
    )

    assert state["event_calls"] == 2
    assert events == [
        {
            "sequence": 1,
            "type": "run-completed",
            "content": "done",
        }
    ]
    assert (
        client._auth_recovery_count
        == 1
    )
