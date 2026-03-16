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


def _healthy_control_payload(service_names):
    return {"services": {name: {"status": "up"} for name in service_names}}


def _runtime_state():
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
        "bootstrap_script": "#!/usr/bin/env bash\nset -e\n",
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


def test_combo_start_uses_resolve_combo_endpoints(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_combo_endpoints"
    ), "Expected combo path dependency on resolve_combo_endpoints(...)"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo path dependency on resolve_runtime_state_for_combo(...)"

    state = _runtime_state()
    captured = {"endpoint_calls": []}

    def _fake_resolve_runtime_state_for_combo(*_args, **_kwargs):
        return state

    def _fake_resolve_combo_endpoints(instance_payload, combo_runtime_input):
        captured["endpoint_calls"].append((instance_payload, combo_runtime_input))
        return {
            "architect_url": "http://34.1.1.1:32080",
            "developer_url": "http://34.1.1.1:32081",
            "stt_url": "http://34.1.1.1:39000",
            "tts_url": "http://34.1.1.1:39001",
            "control_url": "http://34.1.1.1:37999",
        }

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return []

        def search_offers(self, *_args, **_kwargs):
            return [
                SimpleNamespace(
                    id="offer-1",
                    gpu_name="A100_SXM4",
                    gpu_ram_gb=80,
                    reliability=0.99,
                    dph=2.5,
                    inet_up_mbps=120,
                    inet_down_mbps=700,
                    interruptible=False,
                )
            ]

        def create_instance(self, *_args, **_kwargs):
            return {
                "instance_id": "i-123",
                "gpu_name": "A100",
                "dph": 2.5,
                "actual_status": "running",
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "12080"}],
                    "8081/tcp": [{"HostPort": "12081"}],
                    "9000/tcp": [{"HostPort": "19000"}],
                    "9001/tcp": [{"HostPort": "19001"}],
                    "7999/tcp": [{"HostPort": "17999"}],
                },
            }

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-123",
                "gpu_name": "A100",
                "dph": 2.5,
                "actual_status": "running",
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "source": "polled",
            }

    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        _fake_resolve_runtime_state_for_combo,
        raising=False,
    )
    monkeypatch.setattr(cli, "resolve_combo_endpoints", _fake_resolve_combo_endpoints, raising=False)
    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(
            ["architect", "developer", "stt", "tts", "control"]
        ),
        raising=False,
    )

    exit_code = _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])
    _ = exit_code

    assert len(captured["endpoint_calls"]) == 1, "Expected combo start to resolve endpoints once"
    instance_payload, combo_runtime_input = captured["endpoint_calls"][0]
    assert isinstance(instance_payload, dict)
    assert (
        instance_payload.get("source") == "polled"
    ), "Expected endpoint resolution to use polled instance payload"
    assert combo_runtime_input in (
        state,
        state.get("combo_manifest"),
    ), "Expected endpoint resolver input derived from combo runtime state"

    stdout = capsys.readouterr().out.strip()
    if stdout:
        payload = json.loads(stdout)
        assert "deepseek_url" not in payload
        assert "whisper_url" not in payload
