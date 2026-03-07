from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace


def _load_vast_module():
    try:
        return importlib.import_module("ai_orchestrator.provider.vast")
    except ModuleNotFoundError:
        return None


def _load_runtime_script_module():
    try:
        return importlib.import_module("ai_orchestrator.runtime.script")
    except ModuleNotFoundError:
        return None


def _load_combo_loader():
    try:
        return importlib.import_module("ai_orchestrator.combos.loader")
    except ModuleNotFoundError:
        return None


def test_provider_receives_bootstrap_string(monkeypatch):
    vast = _load_vast_module()
    assert vast is not None, "Expected ai_orchestrator.provider.vast module"
    assert hasattr(vast, "VastProvider"), "Expected VastProvider class"
    signature = inspect.signature(vast.VastProvider.create_instance)
    assert list(signature.parameters.keys()) == [
        "self",
        "offer_id",
        "snapshot_version",
        "instance_config",
    ], "Expected provider create_instance(self, offer_id, snapshot_version, instance_config)"
    assert (
        "bootstrap_script" not in signature.parameters
    ), "bootstrap_script must be carried inside instance_config, not as a top-level argument"

    recorded = {"put_payload": None}

    class _FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    def _put(_url, headers=None, json=None, params=None):
        _ = headers, params
        recorded["put_payload"] = json
        return _FakeResponse(200, {"new_contract": "i-123"})

    def _get(_url, headers=None, params=None, json=None):
        _ = headers, params, json
        return _FakeResponse(
            200,
            {"instances": {"gpu_name": "A100", "dph_total": 1.0, "public_ipaddr": "1.2.3.4"}},
        )

    fake_requests = SimpleNamespace(
        put=_put,
        get=_get,
        post=lambda *_a, **_k: _FakeResponse(500, {}),
        delete=lambda *_a, **_k: _FakeResponse(500, {}),
    )
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)

    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")
    bootstrap_script = "#!/usr/bin/env bash\nset -e\necho boot\n"
    instance_config = {
        "bootstrap_script": bootstrap_script,
        "env": {"EXAMPLE_FLAG": "1"},
        "disk": 250,
        "ports": {"architect": 8080},
    }
    assert "bootstrap_script" in instance_config
    assert isinstance(instance_config["bootstrap_script"], str)
    assert instance_config["bootstrap_script"].startswith("#!/usr/bin/env bash")
    provider.create_instance(
        "offer-1",
        "snap-v1",
        instance_config,
    )

    assert recorded["put_payload"] is not None
    assert recorded["put_payload"]["onstart"] == bootstrap_script
    assert isinstance(recorded["put_payload"]["onstart"], str)


def test_bootstrap_not_generated_by_runtime():
    runtime_script = _load_runtime_script_module()
    assert runtime_script is not None, "Expected ai_orchestrator.runtime.script module"
    assert not hasattr(
        runtime_script, "generate_bootstrap_script"
    ), "Runtime layer must not generate bootstrap scripts"


def test_bootstrap_matches_combo_file(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    combos_root = tmp_path / "combos"
    combo_dir = combos_root / "deepseek_whisper"
    combo_dir.mkdir(parents=True, exist_ok=True)

    combo_yaml = "\n".join(
        [
            "schema_version: 1",
            "name: deepseek_whisper",
            "provider: vast",
            "services:",
            "  architect:",
            "    port: 8080",
        ]
    )
    bootstrap_content = "#!/usr/bin/env bash\nset -e\necho exact\n"
    config_yaml = "snapshot_version: v1\n"

    (combo_dir / "combo.yaml").write_text(combo_yaml + "\n", encoding="utf-8")
    (combo_dir / "bootstrap.sh").write_text(bootstrap_content, encoding="utf-8")
    (combo_dir / "config.yaml").write_text(config_yaml, encoding="utf-8")

    combo = loader.load_combo(combos_root, "deepseek_whisper")
    assert combo.bootstrap_script == bootstrap_content
    assert combo.bootstrap_script.encode("utf-8") == bootstrap_content.encode("utf-8")
