from __future__ import annotations

import importlib
import json
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


def test_combo_start_supports_generic_service_names(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"

    captured_render_env = {}
    captured_instance_config = {}

    runtime_state = {
        "combo_name": "neuroflow",
        "combo_manifest": {
            "name": "neuroflow",
            "services": {
                "interpret": {"port": 8080},
                "reasoner": {"port": 8081},
                "rerank": {"port": 8082},
                "stt": {"port": 9000},
                "tts": {"port": 9001},
                "control": {"port": 7999},
            },
        },
        "bootstrap_script": "#!/usr/bin/env bash\nset -e\n",
        "runtime_config": {
            "vast_api_key": "key-123",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "v2-neuroflow-dev-80gb",
            "idle_timeout_seconds": 1200,
            "gpu": {"min_vram_gb": 79},
            "max_dph": 1.0,
            "min_reliability": 0.92,
            "min_inet_up_mbps": 50,
            "min_inet_down_mbps": 150,
            "verified_only": False,
            "allow_interruptible": True,
            "limit": 1,
        },
        "ports": {
            "interpret": 8080,
            "reasoner": 8081,
            "rerank": 8082,
            "stt": 9000,
            "tts": 9001,
            "control": 7999,
        },
        "snapshot_namespace": "v2-neuroflow-dev-80gb_neuroflow",
        "service_registry": object(),
    }

    def _fake_render_bootstrap_script(script, env):
        _ = script
        captured_render_env.update(dict(env))
        return "#!/usr/bin/env bash\n# rendered sentinel\n"

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return []

        def search_offers(self, *_args, **_kwargs):
            return [
                SimpleNamespace(
                    id="12345",
                    gpu_name="A100_PCIE",
                    gpu_ram_gb=80,
                    reliability=0.95,
                    dph=0.95,
                    inet_up_mbps=80,
                    inet_down_mbps=250,
                    interruptible=True,
                )
            ]

        def create_instance(self, _offer_id, _snapshot_version, instance_config):
            captured_instance_config.update(dict(instance_config))
            return {
                "instance_id": "i-neuro-123",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "actual_status": "running",
            }

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "actual_status": "running",
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
            }

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: runtime_state,
        raising=False,
    )
    monkeypatch.setattr(cli, "render_bootstrap_script", _fake_render_bootstrap_script, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_combo_endpoints",
        lambda *_a, **_k: {
            "interpret_url": "http://34.1.1.1:32080",
            "reasoner_url": "http://34.1.1.1:32081",
            "rerank_url": "http://34.1.1.1:32082",
            "stt_url": "http://34.1.1.1:39000",
            "tts_url": "http://34.1.1.1:39001",
            "control_url": "http://34.1.1.1:37999",
        },
        raising=False,
    )

    exit_code = _invoke_main_safely(cli, ["start", "--combo", "neuroflow"])
    assert exit_code == 0, "Expected successful generic combo start contract"

    assert captured_render_env["AI_ORCH_INTERPRET_PORT"] == "8080"
    assert captured_render_env["AI_ORCH_REASONER_PORT"] == "8081"
    assert captured_render_env["AI_ORCH_RERANK_PORT"] == "8082"
    assert captured_render_env["AI_ORCH_STT_PORT"] == "9000"
    assert captured_render_env["AI_ORCH_TTS_PORT"] == "9001"
    assert captured_render_env["AI_ORCH_CONTROL_PORT"] == "7999"
    assert captured_render_env["AI_ORCH_IDLE_TIMEOUT_SECONDS"] == "1200"

    env_payload = captured_instance_config.get("env", {})
    assert env_payload["AI_ORCH_INTERPRET_PORT"] == "8080"
    assert env_payload["AI_ORCH_REASONER_PORT"] == "8081"
    assert env_payload["AI_ORCH_RERANK_PORT"] == "8082"
    assert env_payload["IDLE_TIMEOUT_SECONDS"] == "1200"

    stdio = capsys.readouterr()
    assert stdio.err.strip() == "", "Expected success path to write stdout only"

    payload = json.loads(stdio.out.strip())
    expected_keys = {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "interpret_url",
        "reasoner_url",
        "rerank_url",
        "stt_url",
        "tts_url",
        "control_url",
        "snapshot_version",
        "idle_timeout",
    }
    assert set(payload.keys()) == expected_keys
    assert payload["interpret_url"] == "http://34.1.1.1:32080"
    assert payload["reasoner_url"] == "http://34.1.1.1:32081"
    assert payload["rerank_url"] == "http://34.1.1.1:32082"
