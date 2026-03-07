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


def test_combo2_control_service_port_required(monkeypatch):
    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    combo_manifest_path = Path("combos") / "reasoning_80gb" / "combo.yaml"
    assert combo_manifest_path.is_file(), "Expected combos/reasoning_80gb/combo.yaml asset"

    runtime_state = combo_manager.resolve_runtime_state_for_combo(
        combos_root=Path("combos"),
        combo_name="reasoning_80gb",
        base_config={},
        cli_overrides={},
    )
    manifest = runtime_state.get("combo_manifest", {})
    services = manifest.get("services", {})

    assert "control" in services, "combo.yaml must declare a control service"
    control = services["control"]
    assert isinstance(control, dict), "control service definition must be a mapping"
    assert control.get("port") == 7999, "control service must expose port 7999"

    ports = {
        name: int(service["port"])
        for name, service in services.items()
        if isinstance(service, dict) and "port" in service
    }

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
    provider.create_instance(
        "offer-1",
        "v1-80gb",
        {
            "bootstrap_script": runtime_state.get("bootstrap_script", "#!/usr/bin/env bash\nset -e\n"),
            "ports": ports,
        },
    )

    assert len(recorded_payloads) == 1
    env_mappings = recorded_payloads[0].get("env", {})
    assert isinstance(env_mappings, dict), "Expected env mapping in provider payload"
    assert "-p 7999:7999" in env_mappings, "Runtime must propagate control port into provider mappings"
