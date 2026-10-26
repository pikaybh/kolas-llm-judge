from __future__ import annotations

import asyncio

import httpx
import pytest

from kolas_llm_judge.official_runtime import load_official_runtime
from kolas_llm_judge.sut_client import SeexrSutClient, SutConfig


def test_api_key_auth_takes_priority_and_is_forwarded_on_every_request() -> None:
    seen: list[tuple[str, str]] = []
    key = "sk-" + "c" * 64

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-api-key") == key
        assert "authorization" not in request.headers
        seen.append((request.method, request.url.path))
        if request.url.path.endswith("/agents"):
            return httpx.Response(200, json={"data": {"agents": ["risk-assessment"]}})
        if request.url.path.endswith("/chat/sessions"):
            return httpx.Response(201, json={"data": {"id": "session-1"}})
        if request.url.path.endswith("/agents/risk-assessment/runs"):
            return httpx.Response(202, json={"data": {"runId": "run-1"}})
        if request.url.path.endswith("/agents/runs/run-1/events"):
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text='data: {"seq": 1, "type": "test"}\n\n')
        if request.url.path.endswith("/instructions/me"):
            return httpx.Response(200, json={"data": {"content": ""}})
        if request.url.path.endswith("/users/me/plan"):
            return httpx.Response(200, json={"data": {"usage": {"tokens_used_month": 0, "tokens_limit": None}}})
        raise AssertionError(request.url.path)

    async def exercise() -> None:
        client = SeexrSutClient(SutConfig(
            base_url="https://example.test/api",
            api_key=key,
            token="jwt-that-must-not-be-used",
            email="user@example.test",
            password="must-not-be-used",
        ))
        await client.client.aclose()
        client.client = httpx.AsyncClient(
            base_url=client.config.base_url,
            headers={"Accept": "application/json", "x-api-key": key},
            transport=httpx.MockTransport(handler),
        )
        try:
            await client.ensure_authenticated()
            await client.healthcheck_auth()
            state = await client.evaluation_account_state()
            assert state["saved_instruction_empty"] is True
            assert await client.create_session("KOLAS-CASE-1") == "session-1"
            assert [event async for event in client._iter_sse("run-1")] == [{"seq": 1, "type": "test"}]
            assert client.config.auth_mode == "api_key"
            assert client._auth_recovery_count == 0
        finally:
            await client.client.aclose()

    asyncio.run(exercise())
    assert len(seen) == 5
    assert not any("login" in path or "refresh" in path for _, path in seen)


def test_invalid_api_key_returns_401_without_password_fallback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/agents")
        return httpx.Response(401, json={"message": "Invalid API key"})

    async def exercise() -> None:
        client = SeexrSutClient(
            SutConfig(
                base_url="https://example.test/api",
                api_key="sk-" + "0" * 64,
                email="fallback@example.test",
                password="not-for-fallback",
            )
        )
        await client.client.aclose()
        client.client = httpx.AsyncClient(
            base_url=client.config.base_url,
            headers={"x-api-key": client.config.api_key},
            transport=httpx.MockTransport(handler),
        )
        try:
            with pytest.raises(httpx.HTTPStatusError, match="401"):
                await client.healthcheck_auth()
        finally:
            await client.client.aclose()

    asyncio.run(exercise())


def test_official_runtime_inherits_secret_key_without_freezing_it_in_yaml() -> None:
    runtime = load_official_runtime()
    env = SutConfig(api_key="sk-" + "e" * 64, base_url="https://attacker.example/api")
    config = runtime.sut_config_with_credentials(env)
    assert config.api_key == env.api_key
    assert config.auth_mode == "api_key"
    assert config.base_url == runtime.sut.base_url
