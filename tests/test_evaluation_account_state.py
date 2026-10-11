from __future__ import annotations

import asyncio
import hashlib

import httpx

from kolas_llm_judge.sut_client import (
    SeexrSutClient,
    SutConfig,
)


def _client(handler) -> SeexrSutClient:
    client = SeexrSutClient(
        SutConfig(
            base_url="https://example.test/api",
            token="test-token",
        )
    )
    asyncio.run(client.client.aclose())
    client.client = httpx.AsyncClient(
        base_url=client.config.base_url,
        transport=httpx.MockTransport(handler),
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer test-token",
        },
    )
    return client


def test_evaluation_account_state_accepts_empty_instruction_and_unlimited_allowance() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/instructions/me"):
            return httpx.Response(
                200,
                json={"data": {"content": "  \n"}},
            )
        if request.url.path.endswith("/users/me/plan"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "usage": {
                            "tokens_used_month": 123,
                            "tokens_limit": None,
                        }
                    }
                },
            )
        raise AssertionError(request.url.path)

    client = _client(handler)
    state = asyncio.run(
        client.evaluation_account_state()
    )
    asyncio.run(client.client.aclose())

    assert state["saved_instruction_empty"] is True
    assert state["saved_instruction_sha256"] == hashlib.sha256(b"").hexdigest()
    assert state["allowance_available"] is True


def test_evaluation_account_state_blocks_personalization_and_exhausted_allowance() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/instructions/me"):
            return httpx.Response(
                200,
                json={"data": {"content": "custom instruction"}},
            )
        if request.url.path.endswith("/users/me/plan"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "usage": {
                            "tokens_used_month": 1000,
                            "tokens_limit": 1000,
                        }
                    }
                },
            )
        raise AssertionError(request.url.path)

    client = _client(handler)
    state = asyncio.run(
        client.evaluation_account_state()
    )
    asyncio.run(client.client.aclose())

    assert state["saved_instruction_empty"] is False
    assert state["saved_instruction_sha256"] != hashlib.sha256(b"").hexdigest()
    assert state["allowance_available"] is False
