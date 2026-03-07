from __future__ import annotations

import importlib
import json
from types import SimpleNamespace


def _load_vast_module():
    try:
        return importlib.import_module("ai_orchestrator.provider.vast")
    except ModuleNotFoundError:
        return None


def test_combo2_port_mapping_order_deterministic(monkeypatch):
    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    recorded_payloads: list[dict] = []

    class _FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    def _put(_url, headers=None, json=None, params=None):
        _ = headers, params
        recorded_payloads.append(json)
        return _FakeResponse(200, {"new_contract": "i-123"})

    def _get(_url, headers=None, params=None, json=None):
        _ = headers, params, json
        return _FakeResponse(
            200,
            {
                "instances": {
                    "gpu_name": "A100",
                    "dph_total": 2.4,
                    "public_ipaddr": "1.2.3.4",
                    "actual_status": "running",
                }
            },
        )

    fake_requests = SimpleNamespace(
        put=_put,
        get=_get,
        post=lambda *_a, **_k: _FakeResponse(500, {}),
        delete=lambda *_a, **_k: _FakeResponse(500, {}),
    )
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)

    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    instance_config = {
        "bootstrap_script": "#!/usr/bin/env bash\nset -e\necho boot\n",
        "ports": {
            "control": 7999,
            "developer": 8081,
            "architect": 8080,
            "tts": 9001,
            "stt": 9000,
        },
    }

    provider.create_instance("offer-1", "snap-v1", instance_config)
    provider.create_instance("offer-1", "snap-v1", instance_config)

    assert len(recorded_payloads) == 2
    first_env_keys = list(recorded_payloads[0]["env"].keys())
    second_env_keys = list(recorded_payloads[1]["env"].keys())

    def _extract_exposed_ports(env_keys: list[str]) -> list[int]:
        ports: list[int] = []
        for key in env_keys:
            assert key.startswith("-p "), "Expected Vast payload env key to use -p <port>:<port>"
            mapping = key[len("-p ") :]
            left, right = mapping.split(":", 1)
            assert left == right, "Expected symmetric container-to-host port exposure"
            ports.append(int(left))
        return ports

    expected_ports = sorted(instance_config["ports"].values())
    first_exposed_ports = _extract_exposed_ports(first_env_keys)
    second_exposed_ports = _extract_exposed_ports(second_env_keys)

    assert sorted(first_exposed_ports) == expected_ports
    assert sorted(second_exposed_ports) == expected_ports
    assert first_exposed_ports == second_exposed_ports

    first_canonical = json.dumps(recorded_payloads[0], sort_keys=True)
    second_canonical = json.dumps(recorded_payloads[1], sort_keys=True)
    assert first_canonical == second_canonical


def test_combo2_disk_propagation(monkeypatch):
    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    recorded_payloads: list[dict] = []

    class _FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    def _put(_url, headers=None, json=None, params=None):
        _ = headers, params
        recorded_payloads.append(json)
        return _FakeResponse(200, {"new_contract": "i-123"})

    def _get(_url, headers=None, params=None, json=None):
        _ = headers, params, json
        return _FakeResponse(
            200,
            {
                "instances": {
                    "gpu_name": "A100",
                    "dph_total": 2.4,
                    "public_ipaddr": "1.2.3.4",
                    "actual_status": "running",
                }
            },
        )

    fake_requests = SimpleNamespace(
        put=_put,
        get=_get,
        post=lambda *_a, **_k: _FakeResponse(500, {}),
        delete=lambda *_a, **_k: _FakeResponse(500, {}),
    )
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)

    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    instance_config = {
        "bootstrap_script": "#!/usr/bin/env bash\nset -e\necho boot\n",
        "disk": 250,  # config.min_disk_gb
        "ports": {"architect": 8080, "stt": 9000, "control": 7999},
    }

    provider.create_instance("offer-1", "snap-v1", instance_config)

    assert len(recorded_payloads) == 1
    payload = recorded_payloads[0]
    assert "disk" in payload
    assert payload["disk"] == 250
