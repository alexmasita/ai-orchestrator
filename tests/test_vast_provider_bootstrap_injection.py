import importlib
from types import SimpleNamespace

import pytest


VAST_MODULE = "ai_orchestrator.provider.vast"


def _load_vast_module():
    return importlib.import_module(VAST_MODULE)


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture
def _vast_with_put_recorder(monkeypatch):
    vast = _load_vast_module()
    calls = {"put": [], "post": []}
    state = {
        "put_response": _FakeResponse(
            200,
            {"instance_id": "i-123", "gpu_name": "RTX_4090", "dph": 0.5},
        )
    }

    def _put(url, headers=None, json=None):
        calls["put"].append({"url": url, "headers": headers, "json": json})
        return state["put_response"]

    def _post(url, headers=None, json=None):
        calls["post"].append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(500, {})

    fake_requests = SimpleNamespace(
        put=_put,
        post=_post,
        get=lambda *args, **kwargs: _FakeResponse(500, {}),
        delete=lambda *args, **kwargs: _FakeResponse(500, {}),
    )
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)
    return vast, calls, state


def test_vast_provider_class_exists():
    vast = _load_vast_module()
    assert hasattr(vast, "VastProvider")


def test_create_instance_uses_put_asks_endpoint_and_injects_bootstrap_script(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")

    provider.create_instance(
        "offer123",
        "snapshot-v1",
        {"bootstrap_script": "echo boot"},
    )

    assert len(calls["put"]) == 1
    assert len(calls["post"]) == 0
    request = calls["put"][0]
    assert request["url"] == "https://vast.example/api/v0/asks/offer123"
    assert request["json"]["onstart"] == "echo boot"


def test_create_instance_payload_enforces_port_mappings(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")

    provider.create_instance(
        "offer123",
        "snapshot-v1",
        {"bootstrap_script": "echo boot"},
    )

    payload = calls["put"][0]["json"]
    assert payload["env"]["-p 8080:8080"] == "1"
    assert payload["env"]["-p 9000:9000"] == "1"


def test_create_instance_preserves_bootstrap_script_exactly(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    original_script = " echo boot\n"

    provider.create_instance(
        "offer123",
        "snapshot-v1",
        {"bootstrap_script": original_script},
    )

    payload = calls["put"][0]["json"]
    assert payload["onstart"] == original_script


def test_create_instance_payload_is_deterministic_for_identical_calls(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    instance_config = {"bootstrap_script": "echo boot"}

    provider.create_instance("offer123", "snapshot-v1", instance_config)
    provider.create_instance("offer123", "snapshot-v1", instance_config)

    assert len(calls["put"]) == 2
    first = calls["put"][0]["json"]
    second = calls["put"][1]["json"]
    assert first == second


def test_create_instance_missing_bootstrap_script_raises_value_error_and_skips_put(
    _vast_with_put_recorder,
):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")

    with pytest.raises(ValueError):
        provider.create_instance("offer123", "snapshot-v1", {})

    assert calls["put"] == []
