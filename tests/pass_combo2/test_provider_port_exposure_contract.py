from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace


def _load_combo_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def _load_vast_module():
    try:
        return importlib.import_module("ai_orchestrator.provider.vast")
    except ModuleNotFoundError:
        return None


def _extract_port_from_mapping(mapping_key: str) -> int:
    assert mapping_key.startswith("-p "), "Expected Vast env mapping key format '-p <port>:<port>'"
    mapping = mapping_key[len("-p ") :]
    left, right = mapping.split(":", 1)
    assert left == right, "Expected symmetric container-to-host port mapping"
    return int(left)


def test_provider_port_exposure_matches_manifest(monkeypatch):
    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    runtime_state = combo_manager.resolve_runtime_state_for_combo(
        combos_root=Path("combos"),
        combo_name="reasoning_80gb",
        base_config={},
        cli_overrides={},
    )
    assert isinstance(runtime_state, dict), "Expected runtime state mapping"
    assert "ports" in runtime_state, "Expected runtime_state['ports'] contract derived from combo manifest"

    ports = runtime_state["ports"]
    assert isinstance(ports, dict), "Expected runtime_state['ports'] to be a dict"
    expected_service_names = {"architect", "developer", "stt", "tts", "control"}
    assert set(ports.keys()) == expected_service_names, "Expected all Combo2 services to be exposed"

    combo_manifest = runtime_state.get("combo_manifest", {})
    assert isinstance(combo_manifest, dict), "Expected combo_manifest in runtime state"
    manifest_services = combo_manifest.get("services", {})
    assert isinstance(manifest_services, dict), "Expected services mapping in combo manifest"

    expected_manifest_ports = sorted(
        int(manifest_services[name]["port"]) for name in sorted(expected_service_names)
    )
    expected_runtime_ports = sorted(int(port) for port in ports.values())
    assert (
        expected_runtime_ports == expected_manifest_ports
    ), "Expected runtime ports to match combo manifest exactly"

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
        "bootstrap_script": runtime_state.get("bootstrap_script", "#!/usr/bin/env bash\nset -e\n"),
        "ports": ports,
    }

    provider.create_instance("offer-1", "snap-v1", instance_config)
    provider.create_instance("offer-1", "snap-v1", instance_config)

    assert len(recorded_payloads) == 2, "Expected deterministic payload generation across repeated calls"

    first_env = recorded_payloads[0]["env"]
    second_env = recorded_payloads[1]["env"]
    assert isinstance(first_env, dict)
    assert isinstance(second_env, dict)

    first_port_keys = [key for key in first_env.keys() if key.startswith("-p ")]
    second_port_keys = [key for key in second_env.keys() if key.startswith("-p ")]

    first_ports = [_extract_port_from_mapping(key) for key in first_port_keys]
    second_ports = [_extract_port_from_mapping(key) for key in second_port_keys]

    assert first_ports == sorted(
        expected_manifest_ports
    ), "Expected provider payload port mapping order sorted by numeric port"
    assert second_ports == sorted(
        expected_manifest_ports
    ), "Expected repeated create_instance calls to preserve deterministic port order"
    assert first_port_keys == second_port_keys, "Expected stable deterministic env key order"
    assert all(
        first_env[key] == "1" for key in first_port_keys
    ), "Expected Vast payload env mapping values to use string '1'"

