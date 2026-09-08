from kolas_llm_judge.sut_client import SutConfig, _normalize_base_url


def test_base_url_normalization() -> None:
    assert _normalize_base_url("https://api.seexr.dev") == "https://api.seexr.dev/api"
    assert _normalize_base_url("https://api.seexr.dev/") == "https://api.seexr.dev/api"
    assert _normalize_base_url("https://host.example/custom") == "https://host.example/custom"


def test_auth_mode() -> None:
    assert SutConfig(token="abc").auth_mode == "token"
    assert SutConfig(email="e@example.com", password="p").auth_mode == "email_password"
    assert SutConfig().auth_mode == "missing"
