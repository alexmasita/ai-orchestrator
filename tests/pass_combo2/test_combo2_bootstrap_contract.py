from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace


def _load_combo_loader_module():
    try:
        return importlib.import_module("ai_orchestrator.combos.loader")
    except ModuleNotFoundError:
        return None


def _load_combo_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def _load_runtime_script_module():
    try:
        return importlib.import_module("ai_orchestrator.runtime.script")
    except ModuleNotFoundError:
        return None


def _load_vast_module():
    try:
        return importlib.import_module("ai_orchestrator.provider.vast")
    except ModuleNotFoundError:
        return None


def test_combo2_env_injection_precedes_bootstrap_body():
    runtime_script = _load_runtime_script_module()
    assert runtime_script is not None, "Expected ai_orchestrator.runtime.script module"
    assert hasattr(
        runtime_script, "render_bootstrap_script"
    ), "Expected render_bootstrap_script(script, env) contract"

    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    combo_bootstrap_path = Path("combos") / "reasoning_80gb" / "bootstrap.sh"
    assert combo_bootstrap_path.is_file(), "Expected combos/reasoning_80gb/bootstrap.sh asset"

    runtime_state = combo_manager.resolve_runtime_state_for_combo(
        combos_root=Path("combos"),
        combo_name="reasoning_80gb",
        base_config={},
        cli_overrides={},
    )
    assert isinstance(runtime_state, dict), "Expected runtime state mapping"
    assert "bootstrap_script" in runtime_state, "Expected bootstrap_script in runtime state"

    original_script = runtime_state["bootstrap_script"]
    assert isinstance(original_script, str), "Expected runtime_state['bootstrap_script'] to be a str"
    rendered = runtime_script.render_bootstrap_script(original_script, {"ZZZ": "3", "AAA": "1"})

    assert isinstance(rendered, str)
    assert rendered.startswith("#!/usr/bin/env bash")

    # Env must be injected before the original script body.
    first_body_line = original_script.splitlines()[1] if len(original_script.splitlines()) > 1 else ""
    assert rendered.find("AAA") < rendered.find(first_body_line)
    assert rendered.find("ZZZ") < rendered.find(first_body_line)

    # Bootstrap script body must remain byte-identical.
    original_body = "\n".join(original_script.splitlines()[1:])
    rendered_body = "\n".join(rendered.splitlines()[1 + 2 :])
    assert rendered_body.encode("utf-8") == original_body.encode("utf-8")


def test_combo2_bootstrap_body_preserved(monkeypatch):
    loader = _load_combo_loader_module()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    combo_bootstrap_path = Path("combos") / "reasoning_80gb" / "bootstrap.sh"
    assert combo_bootstrap_path.is_file(), "Expected combos/reasoning_80gb/bootstrap.sh asset"

    combo = loader.load_combo(Path("combos"), "reasoning_80gb")
    original_body = "\n".join(combo.bootstrap_script.splitlines()[1:])

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
        "snap-v1",
        {
            "bootstrap_script": combo.bootstrap_script,
            "env": {"AAA": "1"},
            "ports": {"architect": 8080},
        },
    )

    assert len(recorded_payloads) == 1
    onstart_script = recorded_payloads[0]["onstart"]
    assert onstart_script.encode("utf-8") == combo.bootstrap_script.encode("utf-8")

    onstart_body = "\n".join(onstart_script.splitlines()[1:])
    assert onstart_body.encode("utf-8") == original_body.encode("utf-8")


def test_runtime_loads_bootstrap_from_combo_directory(monkeypatch):
    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class contract"

    combo_name = "reasoning_80gb"
    combo_bootstrap_path = Path("combos") / combo_name / "bootstrap.sh"
    assert combo_bootstrap_path.is_file(), "Expected combos/reasoning_80gb/bootstrap.sh asset"

    expected_bootstrap = combo_bootstrap_path.read_text(encoding="utf-8")
    runtime_state = combo_manager.resolve_runtime_state_for_combo(
        combos_root=Path("combos"),
        combo_name=combo_name,
        base_config={},
        cli_overrides={},
    )
    assert "bootstrap_script" in runtime_state, "Expected bootstrap_script in runtime state"
    runtime_bootstrap = runtime_state["bootstrap_script"]
    assert isinstance(runtime_bootstrap, str)

    # Runtime must load the combo bootstrap exactly instead of generating a new script.
    assert runtime_bootstrap.encode("utf-8") == expected_bootstrap.encode("utf-8")

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
        "snap-v1",
        {
            "bootstrap_script": runtime_bootstrap,
            "env": {"AAA": "1"},
            "ports": {"architect": 8080},
        },
    )

    assert len(recorded_payloads) == 1
    onstart_script = recorded_payloads[0]["onstart"]
    assert onstart_script.encode("utf-8") == expected_bootstrap.encode("utf-8")

    expected_body = "\n".join(expected_bootstrap.splitlines()[1:])
    onstart_body = "\n".join(onstart_script.splitlines()[1:])
    assert onstart_body.encode("utf-8") == expected_body.encode("utf-8")
