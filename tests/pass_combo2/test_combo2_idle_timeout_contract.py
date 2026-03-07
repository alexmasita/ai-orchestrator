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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_combo2_fixture(combos_root: Path) -> None:
    combo_dir = combos_root / "reasoning_80gb"
    _write(
        combo_dir / "combo.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "name: reasoning_80gb",
                "provider: vast",
                "services:",
                "  control:",
                "    port: 7999",
                "    health_path: /health",
            ]
        )
        + "\n",
    )
    _write(
        combo_dir / "bootstrap.sh",
        "\n".join(["#!/usr/bin/env bash", "set -e", "echo boot"]) + "\n",
    )
    _write(combo_dir / "config.yaml", "idle_timeout_seconds: 1800\n")


def test_combo2_idle_timeout_env_propagation(monkeypatch, tmp_path):
    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    combos_root = tmp_path / "combos"
    _create_combo2_fixture(combos_root)

    runtime_state = combo_manager.resolve_runtime_state_for_combo(
        combos_root=combos_root,
        combo_name="reasoning_80gb",
        base_config={},
        cli_overrides={},
    )
    runtime_config = runtime_state.get("runtime_config", {})
    assert runtime_config.get("idle_timeout_seconds") == 1800

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
            "bootstrap_script": runtime_state["bootstrap_script"],
            "ports": {"control": 7999},
            "env": {"IDLE_TIMEOUT_SECONDS": str(runtime_config["idle_timeout_seconds"])},
        },
    )

    assert len(recorded_payloads) == 1
    env_payload = recorded_payloads[0].get("env", {})
    assert "IDLE_TIMEOUT_SECONDS" in env_payload
    assert env_payload["IDLE_TIMEOUT_SECONDS"] == "1800"
