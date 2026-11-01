from kolas_llm_judge.manifest import (
    normalize_sut_source_fingerprint, sut_source_fingerprint_matches
)
import pytest


def payload(core="a"*64, agents="b"*64, pid=100):
    return {
        "schema_version": "seexr-sut-source-v1",
        "core": {
            "component": "core", "artifact_sha256": core,
            "process_pid": pid, "process_start_utc": "2026-11-01T00:00:00Z"
        },
        "agents": {
            "component": "agents", "artifact_sha256": agents,
            "process_pid": 200, "process_start_utc": "2026-11-01T00:00:00Z"
        },
    }


def test_real_artifact_hash_changes_procedure_invalid():
    a = payload()
    assert sut_source_fingerprint_matches(a, payload())
    assert not sut_source_fingerprint_matches(a, payload(core="f"*64))
    assert not sut_source_fingerprint_matches(a, payload(agents="f"*64))
    assert not sut_source_fingerprint_matches(a, payload(pid=101))


def test_missing_component_or_hash_fails_closed():
    a = payload()
    del a["agents"]
    with pytest.raises(ValueError):
        normalize_sut_source_fingerprint(a)
    assert not sut_source_fingerprint_matches(a,payload())
    with pytest.raises(ValueError):
        normalize_sut_source_fingerprint(payload(core="invalid"))


def test_sut_key_inaccessible_to_plain_jwt(monkeypatch):
    from kolas_llm_judge.sut_client import SeexrSutClient, SutConfig
    import asyncio
    async def call():
        async with SeexrSutClient(SutConfig(api_key=None,token="jwt")) as sut:
            await sut.sut_source_fingerprint()
    with pytest.raises(RuntimeError, match="SEEXR_API_KEY"):
        asyncio.run(call())
