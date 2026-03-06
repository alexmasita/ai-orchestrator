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
        self.text = ""

    def json(self):
        return self._payload


@pytest.fixture
def _vast_with_retry_state(monkeypatch):
    vast = _load_vast_module()
    calls = {"put": [], "get": [], "post": []}
    state = {
        "put_responses": [],
        "post_responses": [],
        "get_response": _FakeResponse(
            200,
            {"instances": {"gpu_name": "RTX_4090", "dph_total": 0.5, "public_ipaddr": "1.2.3.4"}},
        ),
    }

    class _RequestException(Exception):
        pass

    def _put(url, headers=None, params=None, json=None):
        calls["put"].append({"url": url, "headers": headers, "params": params, "json": json})
        if not state["put_responses"]:
            return _FakeResponse(500, {"msg": "missing test response"})
        return state["put_responses"].pop(0)

    def _get(url, headers=None, params=None, json=None):
        calls["get"].append({"url": url, "headers": headers, "params": params, "json": json})
        return state["get_response"]

    def _post(url, headers=None, params=None, json=None):
        calls["post"].append({"url": url, "headers": headers, "params": params, "json": json})
        if state["post_responses"]:
            return state["post_responses"].pop(0)
        return _FakeResponse(200, {"offers": []})

    fake_requests = SimpleNamespace(
        exceptions=SimpleNamespace(RequestException=_RequestException),
        put=_put,
        get=_get,
        post=_post,
        delete=lambda *_args, **_kwargs: _FakeResponse(500, {}),
    )
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)
    return vast, calls, state


def _offer_payload(offer_id):
    return {
        "id": offer_id,
        "gpu_name": "RTX_4090",
        "gpu_ram": 24,
        "reliability2": 0.99,
        "dph_total": 0.5,
        "inet_up": 1000.0,
        "inet_down": 1000.0,
        "interruptible": False,
    }


def test_retry_once_on_no_such_ask_then_success(_vast_with_retry_state):
    vast, calls, state = _vast_with_retry_state
    state["post_responses"] = [
        _FakeResponse(200, {"offers": [_offer_payload("1001"), _offer_payload("1002")]}),
        _FakeResponse(200, {"offers": [_offer_payload("1001"), _offer_payload("1002")]}),
    ]
    state["put_responses"] = [
        _FakeResponse(400, {"msg": "error 404/3603: no_such_ask", "error": "invalid_args"}),
        _FakeResponse(200, {"new_contract": "i-2"}),
    ]
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    provider.search_offers({"required_vram_gb": 24})

    instance = provider.create_instance(
        "1001",
        "snapshot-v1",
        {"bootstrap_script": "echo boot"},
    )

    assert len(calls["put"]) == 2
    assert len(calls["post"]) == 2
    assert calls["post"][0]["json"] == calls["post"][1]["json"]
    assert calls["put"][0]["url"] == "https://vast.example/api/v0/asks/1001"
    assert calls["put"][1]["url"] == "https://vast.example/api/v0/asks/1002"
    assert calls["put"][0]["json"] == calls["put"][1]["json"]
    assert calls["put"][0]["json"]["onstart"] == "echo boot"
    assert len(calls["get"]) == 1
    assert calls["get"][0]["url"] == "https://vast.example/api/v0/instances/i-2"
    assert instance.instance_id == "i-2"


def test_retry_cap_two_attempts_only_for_stale_ask(_vast_with_retry_state):
    vast, calls, state = _vast_with_retry_state
    state["post_responses"] = [
        _FakeResponse(200, {"offers": [_offer_payload("1001"), _offer_payload("1002")]}),
        _FakeResponse(200, {"offers": [_offer_payload("1001"), _offer_payload("1002")]}),
    ]
    state["put_responses"] = [
        _FakeResponse(400, {"msg": "no_such_ask", "error": "invalid_args"}),
        _FakeResponse(400, {"msg": "no_such_ask", "error": "invalid_args"}),
    ]
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    provider.search_offers({"required_vram_gb": 24})

    with pytest.raises(vast.VastProviderError, match="no_such_ask"):
        provider.create_instance(
            "1001",
            "snapshot-v1",
            {"bootstrap_script": "echo boot"},
        )

    assert len(calls["put"]) == 2
    assert len(calls["post"]) == 2
    assert calls["post"][0]["json"] == calls["post"][1]["json"]
    assert calls["put"][0]["url"] == "https://vast.example/api/v0/asks/1001"
    assert calls["put"][1]["url"] == "https://vast.example/api/v0/asks/1002"
    assert calls["get"] == []


def test_non_retryable_error_does_not_retry(_vast_with_retry_state):
    vast, calls, state = _vast_with_retry_state
    state["post_responses"] = [
        _FakeResponse(200, {"offers": [_offer_payload("1001"), _offer_payload("1002")]}),
    ]
    state["put_responses"] = [
        _FakeResponse(400, {"msg": "permission denied", "error": "forbidden"}),
    ]
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    provider.search_offers({"required_vram_gb": 24})

    with pytest.raises(vast.VastProviderError, match="permission denied"):
        provider.create_instance(
            "1001",
            "snapshot-v1",
            {"bootstrap_script": "echo boot"},
        )

    assert len(calls["put"]) == 1
    assert len(calls["post"]) == 1
    assert calls["put"][0]["url"] == "https://vast.example/api/v0/asks/1001"
    assert calls["get"] == []


def test_stale_ask_without_cached_requirements_does_not_retry(_vast_with_retry_state):
    vast, calls, state = _vast_with_retry_state
    state["put_responses"] = [
        _FakeResponse(400, {"msg": "no_such_ask", "error": "invalid_args"}),
    ]
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")

    with pytest.raises(vast.VastProviderError, match="no_such_ask"):
        provider.create_instance(
            "1001",
            "snapshot-v1",
            {"bootstrap_script": "echo boot"},
        )

    assert len(calls["put"]) == 1
    assert len(calls["post"]) == 0
    assert calls["put"][0]["url"] == "https://vast.example/api/v0/asks/1001"
    assert calls["get"] == []


def test_refresh_returns_no_new_offer_no_retry_attempt(_vast_with_retry_state):
    vast, calls, state = _vast_with_retry_state
    state["post_responses"] = [
        _FakeResponse(200, {"offers": [_offer_payload("1001")]}),
        _FakeResponse(200, {"offers": [_offer_payload("1001")]}),
    ]
    state["put_responses"] = [
        _FakeResponse(400, {"msg": "no_such_ask", "error": "invalid_args"}),
    ]
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    provider.search_offers({"required_vram_gb": 24})

    with pytest.raises(vast.VastProviderError, match="no_such_ask"):
        provider.create_instance(
            "1001",
            "snapshot-v1",
            {"bootstrap_script": "echo boot"},
        )

    assert len(calls["post"]) == 2
    assert len(calls["put"]) == 1
    assert calls["put"][0]["url"] == "https://vast.example/api/v0/asks/1001"
