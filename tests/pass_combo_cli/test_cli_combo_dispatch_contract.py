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


def test_combo_start_dispatches_to_combo_runtime_state(monkeypatch):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start to depend on resolve_runtime_state_for_combo(...) contract"

    calls = {"resolver": 0, "legacy": 0}

    def _fake_resolve_runtime_state_for_combo(*_args, **_kwargs):
        calls["resolver"] += 1
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

    def _legacy_run_orchestration(*_args, **_kwargs):
        calls["legacy"] += 1
        raise AssertionError("Legacy run_orchestration path must not execute for combo start")

    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        _fake_resolve_runtime_state_for_combo,
        raising=False,
    )
    monkeypatch.setattr(cli, "run_orchestration", _legacy_run_orchestration, raising=False)

    _invoke_main_safely(cli, ["start", "--combo", "reasoning_80gb"])

    assert calls["resolver"] == 1, "Expected combo resolver to be invoked exactly once"
    assert calls["legacy"] == 0, "Expected legacy orchestration path to remain unused"


def test_combo_start_searches_offers_before_create_and_uses_selected_offer_id(monkeypatch):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "main"), "Expected main(argv=None) CLI entrypoint"
    assert hasattr(
        cli, "resolve_runtime_state_for_combo"
    ), "Expected combo start to depend on resolve_runtime_state_for_combo(...) contract"

    calls: list[str] = []
    captured = {"offer_id": None}

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

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return []

        def search_offers(self, _requirements):
            calls.append("search_offers")
            return [
                SimpleNamespace(
                    id="9876543",
                    gpu_name="A100_SXM4",
                    gpu_ram_gb=80,
                    reliability=0.99,
                    dph=2.5,
                    inet_up_mbps=120,
                    inet_down_mbps=600,
                    interruptible=False,
                )
            ]

        def create_instance(self, offer_id, _snapshot_version, _instance_config):
            calls.append("create_instance")
            captured["offer_id"] = str(offer_id)
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

    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        _fake_resolve_runtime_state_for_combo,
        raising=False,
    )
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
    assert exit_code == 0
    assert calls == [
        "search_offers",
        "create_instance",
    ], "Expected deterministic call order: search_offers then create_instance"
    assert captured["offer_id"] == "9876543"
    assert captured["offer_id"] != "combo"
