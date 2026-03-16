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


def test_combo_start_refuses_if_instance_exists(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start dependency on resolve_runtime_state_for_combo(...)"

    calls = {"list_instances": 0, "create_instance": 0}

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            calls["list_instances"] += 1
            return [{"instance_id": "i-existing", "actual_status": "running"}]

        def create_instance(self, *_args, **_kwargs):
            calls["create_instance"] += 1
            return {"instance_id": "i-should-not-create"}

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(cli, "resolve_runtime_state_for_combo", lambda *_a, **_k: _runtime_state(), raising=False)

    exit_code = _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])

    assert calls["list_instances"] >= 1, "Expected combo start to check provider.list_instances()"
    assert calls["create_instance"] == 0, "Expected default guard to block create when instance exists"
    assert exit_code != 0, "Expected non-zero exit when guard blocks launch"
    stdio = capsys.readouterr()
    assert stdio.out.strip() == "", "Expected no stdout JSON on guard failure"
    assert stdio.err.strip() != "", "Expected deterministic error text on stderr"


def test_combo_start_allows_multiple_with_flag(monkeypatch):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start dependency on resolve_runtime_state_for_combo(...)"

    calls = {"list_instances": 0, "create_instance": 0}

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            calls["list_instances"] += 1
            return [{"instance_id": "i-existing", "actual_status": "running"}]

        def search_offers(self, *_args, **_kwargs):
            return [
                SimpleNamespace(
                    id="12345",
                    gpu_name="A100_SXM4",
                    gpu_ram_gb=80,
                    reliability=0.99,
                    dph=2.5,
                    inet_up_mbps=140,
                    inet_down_mbps=700,
                    interruptible=False,
                )
            ]

        def create_instance(self, *_args, **_kwargs):
            calls["create_instance"] += 1
            return {
                "instance_id": "i-created",
                "gpu_name": "A100",
                "dph": 2.5,
                "actual_status": "running",
            }

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-created",
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
            }

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(cli, "resolve_runtime_state_for_combo", lambda *_a, **_k: _runtime_state(), raising=False)
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(
            ["architect", "developer", "stt", "tts", "control"]
        ),
        raising=False,
    )

    _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb", "--allow-multiple"])

    assert calls["list_instances"] >= 1, "Expected provider guard check to remain in place"
    assert calls["create_instance"] >= 1, "Expected --allow-multiple to permit create path"


def test_combo_start_guard_ignores_inactive_instance_statuses(monkeypatch):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start dependency on resolve_runtime_state_for_combo(...)"

    calls = {"create_instance": 0}

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return [
                {"instance_id": "i-stopped", "status": "stopped"},
                {"instance_id": "i-exited", "actual_status": "exited"},
                {"instance_id": "i-deleted", "state": "destroyed"},
            ]

        def search_offers(self, *_args, **_kwargs):
            return [
                SimpleNamespace(
                    id="12345",
                    gpu_name="A100_SXM4",
                    gpu_ram_gb=80,
                    reliability=0.99,
                    dph=2.5,
                    inet_up_mbps=140,
                    inet_down_mbps=700,
                    interruptible=False,
                )
            ]

        def create_instance(self, *_args, **_kwargs):
            calls["create_instance"] += 1
            return {
                "instance_id": "i-created",
                "gpu_name": "A100",
                "dph": 2.5,
                "actual_status": "running",
            }

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-created",
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
            }

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli, "resolve_runtime_state_for_combo", lambda *_a, **_k: _runtime_state(), raising=False
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(
            ["architect", "developer", "stt", "tts", "control"]
        ),
        raising=False,
    )

    exit_code = _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])
    assert exit_code == 0
    assert calls["create_instance"] == 1, "Expected inactive instances to be ignored by guard"
