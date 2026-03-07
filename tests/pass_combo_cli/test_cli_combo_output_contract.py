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


def test_combo_start_success_output_schema_locked(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(cli, "format_json_output"), "Expected format_json_output(payload) contract"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start dependency on resolve_runtime_state_for_combo(...)"

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
                    dph=2.5,
                    inet_up_mbps=100,
                    inet_down_mbps=600,
                    interruptible=False,
                )
            ]

        def create_instance(self, *_args, **_kwargs):
            return {
                "instance_id": "i-123",
                "gpu_name": "A100_SXM4",
                "dph": 2.5,
                "actual_status": "running",
            }

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-123",
                "gpu_name": "A100_SXM4",
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
            }

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(cli, "resolve_runtime_state_for_combo", lambda *_a, **_k: _runtime_state(), raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_combo_endpoints",
        lambda *_a, **_k: {
            "architect_url": "http://34.1.1.1:32080",
            "developer_url": "http://34.1.1.1:32081",
            "stt_url": "http://34.1.1.1:39000",
            "tts_url": "http://34.1.1.1:39001",
            "control_url": "http://34.1.1.1:37999",
        },
        raising=False,
    )

    exit_code = _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])
    assert exit_code == 0, "Expected successful combo start contract"

    stdio = capsys.readouterr()
    assert stdio.err.strip() == "", "Expected success path to write stdout only"
    out = stdio.out.strip()
    assert out != "", "Expected JSON output on stdout"
    assert "\n" not in out, "Expected one-line deterministic JSON"

    payload = json.loads(out)
    expected_keys = {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "architect_url",
        "developer_url",
        "stt_url",
        "tts_url",
        "control_url",
        "snapshot_version",
        "idle_timeout",
    }
    assert set(payload.keys()) == expected_keys
    assert list(payload.keys()) == sorted(payload.keys()), "Expected deterministic canonical key ordering"


def test_combo_start_errors_go_to_stderr_only(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start dependency on resolve_runtime_state_for_combo(...)"

    def _raise_runtime_state_error(*_args, **_kwargs):
        raise RuntimeError("combo runtime failure")

    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        _raise_runtime_state_error,
        raising=False,
    )

    exit_code = _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])

    assert exit_code != 0, "Expected non-zero exit on combo start failure"
    stdio = capsys.readouterr()
    assert stdio.out.strip() == "", "Expected no stdout JSON on failure"
    assert stdio.err.strip() != "", "Expected error text on stderr"
