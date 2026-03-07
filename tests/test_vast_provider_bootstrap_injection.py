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
    calls = {"put": [], "post": [], "get": []}
    state = {
        "put_response": _FakeResponse(
            200,
            {"new_contract": "i-123"},
        ),
        "get_response": _FakeResponse(
            200,
            {"instances": {"gpu_name": "RTX_4090", "dph_total": 0.5, "public_ipaddr": "1.2.3.4"}},
        ),
    }

    def _put(url, headers=None, json=None):
        calls["put"].append({"url": url, "headers": headers, "json": json})
        return state["put_response"]

    def _get(url, headers=None, params=None, json=None):
        calls["get"].append({"url": url, "headers": headers, "params": params, "json": json})
        return state["get_response"]

    def _post(url, headers=None, json=None):
        calls["post"].append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(500, {})

    fake_requests = SimpleNamespace(
        put=_put,
        get=_get,
        post=_post,
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
    assert len(calls["get"]) == 1
    assert len(calls["post"]) == 0
    request = calls["put"][0]
    assert request["url"] == "https://vast.example/api/v0/asks/offer123"
    assert request["json"]["onstart"] == "echo boot"
    assert calls["get"][0]["url"] == "https://vast.example/api/v0/instances/i-123"


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
    assert len(calls["get"]) == 2
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
    assert calls["get"] == []


def test_create_instance_uses_remote_loader_for_oversized_bootstrap(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    large_script = "#!/usr/bin/env bash\n" + ("echo boot\n" * 600)

    provider.create_instance(
        "offer123",
        "snapshot-v1",
        {
            "bootstrap_script": large_script,
            "combo_name": "reasoning_80gb",
            "bootstrap_base_url": "https://example.invalid/raw",
        },
    )

    payload = calls["put"][0]["json"]
    onstart = payload["onstart"]
    assert onstart.startswith("set -euo pipefail\n")
    assert "curl -fsSL --retry 3 --retry-delay 2 " in onstart
    assert "bash /tmp/ai_orch_bootstrap.sh" in onstart
    assert onstart != large_script
    assert len(onstart.encode("utf-8")) < 4048


def test_create_instance_loader_is_deterministic_for_oversized_bootstrap(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    large_script = "#!/usr/bin/env bash\n" + ("echo boot\n" * 600)
    instance_config = {
        "bootstrap_script": large_script,
        "combo_name": "reasoning_80gb",
        "bootstrap_base_url": "https://example.invalid/raw",
    }

    provider.create_instance("offer123", "snapshot-v1", instance_config)
    provider.create_instance("offer123", "snapshot-v1", instance_config)

    assert len(calls["put"]) == 2
    first_onstart = calls["put"][0]["json"]["onstart"]
    second_onstart = calls["put"][1]["json"]["onstart"]
    assert first_onstart == second_onstart


def test_create_instance_oversized_bootstrap_invalid_combo_name_raises(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    large_script = "#!/usr/bin/env bash\n" + ("echo boot\n" * 600)

    with pytest.raises(vast.VastProviderError, match="Invalid combo_name"):
        provider.create_instance(
            "offer123",
            "snapshot-v1",
            {
                "bootstrap_script": large_script,
                "combo_name": "reasoning 80gb",
            },
        )

    assert calls["put"] == []
    assert calls["get"] == []


def test_create_instance_oversized_loader_enforces_local_preflight(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    large_script = "#!/usr/bin/env bash\n" + ("echo boot\n" * 600)
    huge_base_url = "https://example.invalid/" + ("x" * 5000)

    with pytest.raises(vast.VastProviderError, match="Generated loader exceeds"):
        provider.create_instance(
            "offer123",
            "snapshot-v1",
            {
                "bootstrap_script": large_script,
                "combo_name": "reasoning_80gb",
                "bootstrap_base_url": huge_base_url,
            },
        )

    assert calls["put"] == []
    assert calls["get"] == []


def test_create_instance_bootstrap_base_url_resolution_order(_vast_with_put_recorder):
    vast, calls, _ = _vast_with_put_recorder
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    large_script = "#!/usr/bin/env bash\n" + ("echo boot\n" * 600)

    provider.create_instance(
        "offer123",
        "snapshot-v1",
        {
            "bootstrap_script": large_script,
            "combo_name": "reasoning_80gb",
            "runtime_config": {"bootstrap_base_url": "https://runtime.invalid/base"},
        },
    )
    runtime_onstart = calls["put"][0]["json"]["onstart"]
    assert "https://runtime.invalid/base/combos/reasoning_80gb/bootstrap.sh" in runtime_onstart

    provider.create_instance(
        "offer124",
        "snapshot-v1",
        {
            "bootstrap_script": large_script,
            "combo_name": "reasoning_80gb",
        },
    )
    fallback_onstart = calls["put"][1]["json"]["onstart"]
    assert f"{vast.DEFAULT_BOOTSTRAP_BASE_URL}/combos/reasoning_80gb/bootstrap.sh" in fallback_onstart
