from __future__ import annotations

import importlib
from types import SimpleNamespace


def _load_cli_module():
    try:
        return importlib.import_module("ai_orchestrator.cli")
    except ModuleNotFoundError:
        return None


def _invoke_main_safely(cli, argv):
    try:
        return cli.main(argv)
    except SystemExit as exc:  # pragma: no cover - contract helper
        return exc.code


def test_combo_start_uses_render_bootstrap_script(monkeypatch):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "render_bootstrap_script"
    ), "Expected render_bootstrap_script(script, env) contract in combo start path"

    calls = {"render": 0}
    captured_instance_config = {}
    sentinel_bootstrap = "#!/usr/bin/env bash\n# rendered sentinel\n"

    def _fake_render_bootstrap_script(script, env):
        calls["render"] += 1
        assert isinstance(script, str)
        assert isinstance(env, dict)
        return sentinel_bootstrap

    def _fake_resolve_runtime_state_for_combo(*_args, **_kwargs):
        return {
            "combo_name": "reasoning_80gb",
            "combo_manifest": {
                "name": "reasoning_80gb",
                "services": {
                    "architect": {"port": 8080},
                    "developer": {"port": 8081},
                    "stt": {"port": 9000},
                    "tts": {"port": 9001},
                    "control": {"port": 7999},
                },
            },
            "bootstrap_script": "#!/usr/bin/env bash\nset -e\necho 'combo'\n",
            "runtime_config": {
                "vast_api_key": "key-123",
                "vast_api_url": "https://vast.example/api",
                "snapshot_version": "v1-80gb",
                "idle_timeout_seconds": 1800,
                "gpu": {"min_vram_gb": 79},
                "max_dph": 2.5,
                "min_reliability": 0.99,
                "min_inet_up_mbps": 100,
                "min_inet_down_mbps": 500,
                "verified_only": True,
                "allow_interruptible": False,
                "limit": 1,
            },
            "ports": {
                "architect": 8080,
                "developer": 8081,
                "stt": 9000,
                "tts": 9001,
                "control": 7999,
            },
            "snapshot_namespace": "v1-80gb_reasoning_80gb",
            "service_registry": object(),
        }

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return []

        def search_offers(self, *_args, **_kwargs):
            return [
                SimpleNamespace(
                    id="12345",
                    gpu_name="A100_SXM4",
                    gpu_ram_gb=80,
                    reliability=0.99,
                    dph=2.0,
                    inet_up_mbps=200,
                    inet_down_mbps=800,
                    interruptible=False,
                )
            ]

        def create_instance(self, _offer_id, _snapshot_version, instance_config):
            captured_instance_config.update(dict(instance_config))
            return {
                "instance_id": "i-123",
                "actual_status": "running",
                "gpu_name": "A100_SXM4",
                "dph": 2.0,
            }

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-123",
                "actual_status": "running",
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
            }

    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        _fake_resolve_runtime_state_for_combo,
        raising=False,
    )
    monkeypatch.setattr(cli, "render_bootstrap_script", _fake_render_bootstrap_script, raising=False)
    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)

    _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])

    assert calls["render"] == 1, "Expected render_bootstrap_script to be called exactly once"
    assert (
        captured_instance_config.get("bootstrap_script") == sentinel_bootstrap
    ), "Expected provider payload bootstrap_script to match rendered sentinel"
