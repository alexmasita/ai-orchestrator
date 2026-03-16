from __future__ import annotations

import importlib
import json
from pathlib import Path


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


def _runtime_state(runtime_file_paths=None, restart_transition_timeout_seconds=300):
    return {
        "combo_name": "neuroflow",
        "combo_manifest": {
            "name": "neuroflow",
            "services": {
                "interpret": {"port": 8080, "health_path": "/health"},
                "reasoner": {"port": 8081, "health_path": "/health"},
                "rerank": {"port": 8082, "health_path": "/health"},
                "stt": {"port": 9000, "health_path": "/health"},
                "tts": {"port": 9001, "health_path": "/"},
                "control": {"port": 7999, "health_path": "/health"},
            },
        },
        "bootstrap_script": "#!/usr/bin/env bash\nset -e\n",
        "runtime_config": {
            "vast_api_key": "key-123",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "v2-neuroflow-dev-80gb",
            "idle_timeout_seconds": 1200,
            "restart_transition_timeout_seconds": restart_transition_timeout_seconds,
            "runtime_file_paths": list(runtime_file_paths or []),
            "gpu": {"min_vram_gb": 79},
            "max_dph": 1.0,
            "min_reliability": 0.9,
            "min_inet_up_mbps": 50,
            "min_inet_down_mbps": 150,
            "verified_only": True,
            "allow_interruptible": False,
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


def _healthy_control_payload():
    return {
        "services": {
            "interpret": {"status": "up"},
            "reasoner": {"status": "up"},
            "rerank": {"status": "up"},
            "stt": {"status": "up"},
            "tts": {"status": "up"},
            "control": {"status": "up"},
        }
    }


def _install_fake_clock(cli, monkeypatch):
    current = {"value": 0.0}

    def _monotonic():
        return current["value"]

    def _sleep(seconds):
        current["value"] += float(seconds)

    monkeypatch.setattr(cli.time, "monotonic", _monotonic, raising=False)
    monkeypatch.setattr(cli.time, "sleep", _sleep, raising=False)


def test_combos_command_lists_repo_combos(capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    exit_code = _invoke_main_safely(cli, ["combos"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "neuroflow" in output
    assert "reasoning_80gb" in output


def test_resolve_overwrites_existing_runtime_file(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_file = tmp_path / "runtime.json"
    runtime_file.write_text("old-content", encoding="utf-8")

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            raise AssertionError("Did not expect restart for already running instance")

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )

    exit_code = _invoke_main_safely(
        cli,
        [
            "resolve",
            "--combo",
            "neuroflow",
            "--instance-id",
            "i-neuro-123",
            "--write-runtime-file",
            str(runtime_file),
        ],
    )
    assert exit_code == 0

    stdout_payload = json.loads(capsys.readouterr().out.strip())
    file_payload = json.loads(runtime_file.read_text(encoding="utf-8"))
    assert stdout_payload == file_payload
    assert file_payload["publication_status"] == "success"
    assert file_payload["runtime_file_writes"] == [
        {"path": str(runtime_file.resolve()), "status": "written", "error": None}
    ]
    assert file_payload["control_url"] == "http://34.1.1.1:37999"


def test_resolve_reports_partial_publication_success(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    good_path = tmp_path / "good-runtime.json"
    bad_path = tmp_path / "bad-runtime.json"

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            raise AssertionError("Did not expect restart for already running instance")

    real_atomic_write = cli._atomic_write_text

    def _fake_atomic_write(path: Path, text: str) -> None:
        if path == bad_path.resolve():
            raise OSError("simulated write failure")
        real_atomic_write(path, text)

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr(cli, "_atomic_write_text", _fake_atomic_write, raising=False)

    exit_code = _invoke_main_safely(
        cli,
        [
            "resolve",
            "--combo",
            "neuroflow",
            "--instance-id",
            "i-neuro-123",
            "--write-runtime-file",
            str(good_path),
            "--write-runtime-file",
            str(bad_path),
        ],
    )
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["publication_status"] == "partial"
    assert good_path.exists()
    assert not bad_path.exists()
    write_results = {entry["path"]: entry for entry in payload["runtime_file_writes"]}
    assert write_results[str(good_path.resolve())]["status"] == "written"
    assert write_results[str(bad_path.resolve())]["status"] == "failed"


def test_wizard_restarts_stopped_instance_and_publishes(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_file = tmp_path / "wizard-runtime.json"
    calls = {"set_instance_state": []}

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return [
                {
                    "instance_id": "i-neuro-123",
                    "status": "exited",
                    "actual_status": "exited",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": None,
                    "label": "ai-orch:neuroflow",
                }
            ]

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, instance_id, state):
            calls["set_instance_state"].append((instance_id, state))
            return {"status": "ok"}

    inputs = iter(["1", "1", "1"])

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "_discover_combo_names",
        lambda *_a, **_k: ["neuroflow", "reasoning_80gb"],
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs), raising=False)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)

    exit_code = _invoke_main_safely(
        cli,
        ["wizard", "--write-runtime-file", str(runtime_file)],
    )
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert calls["set_instance_state"] == [("i-neuro-123", "running")]
    assert payload["publication_status"] == "success"
    assert runtime_file.exists()


def test_wizard_ctrl_c_cancels_cleanly(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": (_ for _ in ()).throw(KeyboardInterrupt()),
        raising=False,
    )

    exit_code = _invoke_main_safely(cli, ["wizard"])

    assert exit_code == 130
    captured = capsys.readouterr()
    assert "Available combos:" in captured.out
    assert "Wizard cancelled." in captured.err
    assert "Traceback" not in captured.err


def test_wizard_quit_from_combo_selection_exits_cleanly(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "q", raising=False)

    exit_code = _invoke_main_safely(cli, ["wizard"])

    assert exit_code == 130
    captured = capsys.readouterr()
    assert "Wizard cancelled." in captured.err


def test_wizard_back_from_runtime_step_returns_to_instance_selection(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_file = tmp_path / "wizard-runtime.json"
    inputs = iter(["1", "1", "b", "1", "1"])

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return [
                {
                    "instance_id": "i-neuro-123",
                    "status": "running",
                    "actual_status": "running",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": "34.1.1.1",
                    "label": "ai-orch:neuroflow",
                }
            ]

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            raise AssertionError("Did not expect restart for already running instance")

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "_discover_combo_names",
        lambda *_a, **_k: ["neuroflow", "reasoning_80gb"],
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs), raising=False)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)

    exit_code = _invoke_main_safely(
        cli,
        ["wizard", "--write-runtime-file", str(runtime_file)],
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["publication_status"] == "success"
    assert runtime_file.exists()


def test_wizard_offers_default_runtime_file_when_none_configured(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    inputs = iter(["1", "1", "1"])

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return [
                {
                    "instance_id": "i-neuro-123",
                    "status": "running",
                    "actual_status": "running",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": "34.1.1.1",
                    "label": "ai-orch:neuroflow",
                }
            ]

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            raise AssertionError("Did not expect restart for already running instance")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(cli, "_maybe_load_combo_base_config", lambda *_a, **_k: {}, raising=False)
    monkeypatch.setattr(
        cli,
        "_discover_combo_names",
        lambda *_a, **_k: ["neuroflow", "reasoning_80gb"],
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(runtime_file_paths=[]),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs), raising=False)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)

    exit_code = _invoke_main_safely(cli, ["wizard"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    default_path = (tmp_path / ".ai-orchestrator" / "runtime" / "neuroflow-runtime.json").resolve()
    assert payload["publication_status"] == "success"
    assert default_path.exists()
    assert payload["runtime_file_writes"] == [
        {"path": str(default_path), "status": "written", "error": None}
    ]


def test_resolve_expands_directory_runtime_file_path(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_dir = tmp_path / "consumer-a"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    expected_runtime_file = (runtime_dir / "neuroflow-runtime.json").resolve()

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            raise AssertionError("Did not expect restart for already running instance")

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(runtime_file_paths=[str(runtime_dir)]),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )

    exit_code = _invoke_main_safely(
        cli,
        [
            "resolve",
            "--combo",
            "neuroflow",
            "--instance-id",
            "i-neuro-123",
        ],
    )
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert expected_runtime_file.exists()
    assert payload["runtime_file_writes"] == [
        {"path": str(expected_runtime_file), "status": "written", "error": None}
    ]


def test_resolve_writes_neuroflow_probe_sidecar_when_probe_bundle_exists(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_file = tmp_path / "neuroflow-runtime.json"
    expected_probe_file = tmp_path / "neuroflow-runtime-probes.json"

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def poll_instance(self, _instance_id):
            return {
                "instance_id": "i-neuro-123",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            raise AssertionError("Did not expect restart for already running instance")

    def _fake_bundle(runtime_state, result, health_payload):
        enriched = dict(result)
        enriched["runtime_schema_version"] = "2026-03-15-neuroflow-runtime-v1"
        enriched["runtime_readiness"] = {"live_integration_ready": True, "notes": []}
        enriched["capabilities"] = {"control": {"name": "control"}}
        probe_payload = {
            "runtime_schema_version": "2026-03-15-neuroflow-runtime-probes-v1",
            "resolved_at": result["resolved_at"],
            "capability_probes": {"control": {"probe_http_status": 200}},
        }
        return enriched, probe_payload

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr(cli, "_build_neuroflow_runtime_bundle", _fake_bundle, raising=False)

    exit_code = _invoke_main_safely(
        cli,
        [
            "resolve",
            "--combo",
            "neuroflow",
            "--instance-id",
            "i-neuro-123",
            "--write-runtime-file",
            str(runtime_file),
        ],
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert runtime_file.exists()
    assert expected_probe_file.exists()
    assert payload["runtime_file_writes"] == [
        {"path": str(runtime_file.resolve()), "status": "written", "error": None},
        {"path": str(expected_probe_file.resolve()), "status": "written", "error": None},
    ]


def test_neuroflow_bundle_marks_stt_fixture_probe_success(monkeypatch, tmp_path):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    fixture_path = tmp_path / "stt-probe.wav"
    fixture_path.write_bytes(b"fixture-wav")

    runtime_state = _runtime_state()
    result = {
        "instance_id": "i-neuro-123",
        "status": "ready",
        "resolved_at": "2026-03-15T13:07:50.934421+00:00",
        "gpu_type": "A100_PCIE",
        "cost_per_hour": None,
        "idle_timeout": 1200,
        "snapshot_version": "v2-neuroflow-dev-80gb",
        "interpret_url": "http://34.1.1.1:32080",
        "reasoner_url": "http://34.1.1.1:32081",
        "rerank_url": "http://34.1.1.1:32082",
        "stt_url": "http://34.1.1.1:39000",
        "tts_url": "http://34.1.1.1:39001",
        "control_url": "http://34.1.1.1:37999",
    }
    health_payload = _healthy_control_payload()

    def _fake_json_request(url, **kwargs):
        if url.endswith("/status"):
            return {"ok": True, "http_status": 200, "json": {"status": "ready"}, "duration_ms": 12}
        if url.endswith("/v1/chat/completions"):
            model = kwargs["payload"]["model"]
            return {
                "ok": True,
                "http_status": 200,
                "json": {
                    "id": "chatcmpl-123",
                    "object": "chat.completion",
                    "model": model,
                    "choices": [{"message": {"role": "assistant", "content": "ok", "reasoning": ""}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
                "duration_ms": 15,
            }
        if url.endswith("/rerank"):
            return {
                "ok": True,
                "http_status": 200,
                "json": {
                    "id": "rerank-123",
                    "model": "rerank",
                    "results": [{"index": 0, "relevance_score": 0.9, "document": {"text": "x"}}],
                    "usage": {"prompt_tokens": 3, "total_tokens": 3},
                },
                "duration_ms": 11,
            }
        raise AssertionError(f"Unexpected URL {url}")

    def _fake_http_request(url, **kwargs):
        if url.endswith("/v1/audio/speech"):
            return {
                "ok": True,
                "http_status": 200,
                "headers": {"Content-Type": "audio/mpeg"},
                "body": b"tts-bytes",
                "error": None,
                "duration_ms": 17,
            }
        raise AssertionError(f"Unexpected URL {url}")

    def _fake_multipart_request(url, **kwargs):
        assert url.endswith("/v1/audio/transcriptions")
        assert kwargs["file_bytes"] == b"fixture-wav"
        return {
            "ok": True,
            "http_status": 200,
            "json": {
                "text": "Welcome to Neuroflow.",
                "language": "en",
                "duration": 1.540125,
                "model": "turbo",
            },
            "duration_ms": 18280,
            "error": None,
        }

    monkeypatch.setattr(cli, "_resolve_neuroflow_stt_fixture_path", lambda: fixture_path, raising=False)
    monkeypatch.setattr(cli, "_http_json_request", _fake_json_request, raising=False)
    monkeypatch.setattr(cli, "_http_request", _fake_http_request, raising=False)
    monkeypatch.setattr(cli, "_multipart_form_request", _fake_multipart_request, raising=False)

    enriched, probe_payload = cli._build_neuroflow_runtime_bundle(runtime_state, result, health_payload)

    assert enriched["runtime_readiness"]["live_integration_ready"] is True
    assert enriched["capabilities"]["stt"]["probe_strategy"] == "fixture"
    assert enriched["capabilities"]["stt"]["probe_latency_ms"] == 18280
    assert enriched["capabilities"]["stt"]["probe_error"] is None
    assert probe_payload["capability_probes"]["stt"]["probe_strategy"] == "fixture"
    assert probe_payload["capability_probes"]["stt"]["probe_http_status"] == 200
    assert probe_payload["capability_probes"]["stt"]["probe_latency_ms"] == 18280
    assert probe_payload["capability_probes"]["stt"]["response_sample"]["text"] == "Welcome to Neuroflow."


def test_neuroflow_bundle_reports_stt_generated_failure_diagnostically(monkeypatch):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_state = _runtime_state()
    result = {
        "instance_id": "i-neuro-123",
        "status": "ready",
        "resolved_at": "2026-03-15T13:07:50.934421+00:00",
        "gpu_type": "A100_PCIE",
        "cost_per_hour": None,
        "idle_timeout": 1200,
        "snapshot_version": "v2-neuroflow-dev-80gb",
        "interpret_url": "http://34.1.1.1:32080",
        "reasoner_url": "http://34.1.1.1:32081",
        "rerank_url": "http://34.1.1.1:32082",
        "stt_url": "http://34.1.1.1:39000",
        "tts_url": "http://34.1.1.1:39001",
        "control_url": "http://34.1.1.1:37999",
    }
    health_payload = _healthy_control_payload()

    def _fake_json_request(url, **kwargs):
        if url.endswith("/status"):
            return {"ok": True, "http_status": 200, "json": {"status": "ready"}, "duration_ms": 10}
        if url.endswith("/v1/chat/completions"):
            model = kwargs["payload"]["model"]
            return {
                "ok": True,
                "http_status": 200,
                "json": {
                    "id": "chatcmpl-123",
                    "object": "chat.completion",
                    "model": model,
                    "choices": [{"message": {"role": "assistant", "content": "ok", "reasoning": ""}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
                "duration_ms": 12,
            }
        if url.endswith("/rerank"):
            return {
                "ok": True,
                "http_status": 200,
                "json": {
                    "id": "rerank-123",
                    "model": "rerank",
                    "results": [{"index": 0, "relevance_score": 0.9, "document": {"text": "x"}}],
                    "usage": {"prompt_tokens": 3, "total_tokens": 3},
                },
                "duration_ms": 9,
            }
        raise AssertionError(f"Unexpected URL {url}")

    def _fake_http_request(url, **kwargs):
        if url.endswith("/v1/audio/speech"):
            return {
                "ok": True,
                "http_status": 200,
                "headers": {"Content-Type": "audio/mpeg"},
                "body": b"tts-bytes",
                "error": None,
                "duration_ms": 20,
            }
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(cli, "_resolve_neuroflow_stt_fixture_path", lambda: None, raising=False)
    monkeypatch.setattr(cli, "_build_generated_stt_fixture", lambda _audio: (None, "ffmpeg conversion failed"), raising=False)
    monkeypatch.setattr(cli, "_http_json_request", _fake_json_request, raising=False)
    monkeypatch.setattr(cli, "_http_request", _fake_http_request, raising=False)

    enriched, probe_payload = cli._build_neuroflow_runtime_bundle(runtime_state, result, health_payload)

    assert enriched["runtime_readiness"]["live_integration_ready"] is False
    assert enriched["capabilities"]["stt"]["probe_strategy"] == "unverified"
    assert enriched["capabilities"]["stt"]["probe_incomplete"] is True
    assert enriched["capabilities"]["stt"]["probe_error"] == "ffmpeg conversion failed"
    assert enriched["runtime_readiness"]["notes"] == [
        "STT probe incomplete via unverified: ffmpeg conversion failed."
    ]
    assert probe_payload["capability_probes"]["stt"]["probe_strategy"] == "unverified"
    assert probe_payload["capability_probes"]["stt"]["probe_error"] == "ffmpeg conversion failed"


def test_resolve_restarted_instance_stuck_in_scheduling_errors(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    _install_fake_clock(cli, monkeypatch)

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs
            self.poll_calls = 0

        def poll_instance(self, _instance_id):
            self.poll_calls += 1
            if self.poll_calls == 1:
                return {
                    "instance_id": "i-neuro-123",
                    "status": "exited",
                    "actual_status": "exited",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": None,
                    "ports": {},
                    "label": "ai-orch:neuroflow",
                }
            return {
                "instance_id": "i-neuro-123",
                "status": "scheduling",
                "actual_status": "scheduling",
                "gpu_name": "A100_PCIE",
                "public_ipaddr": None,
                "ports": {},
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            return {"status": "ok"}

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(restart_transition_timeout_seconds=1),
        raising=False,
    )

    exit_code = _invoke_main_safely(
        cli,
        ["resolve", "--combo", "neuroflow", "--instance-id", "i-neuro-123"],
    )

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "restart_transition_timeout_seconds=1" in stderr
    assert "scheduling" in stderr


def test_wizard_destroys_stuck_restarted_instance_and_starts_new(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_file = tmp_path / "wizard-runtime.json"
    calls = {"set_instance_state": [], "destroy_instance": [], "create_instance": 0}
    inputs = iter(["1", "1", "1", "1"])

    _install_fake_clock(cli, monkeypatch)

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return [
                {
                    "instance_id": "i-neuro-old",
                    "status": "exited",
                    "actual_status": "exited",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": None,
                    "label": "ai-orch:neuroflow",
                }
            ]

        def poll_instance(self, instance_id):
            if instance_id == "i-neuro-old":
                return {
                    "instance_id": "i-neuro-old",
                    "status": "scheduling",
                    "actual_status": "scheduling",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": None,
                    "ports": {},
                    "label": "ai-orch:neuroflow",
                }
            return {
                "instance_id": "i-neuro-new",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, instance_id, state):
            calls["set_instance_state"].append((instance_id, state))
            return {"status": "ok"}

        def destroy_instance(self, instance_id):
            calls["destroy_instance"].append(instance_id)
            return {"status": "ok"}

    def _fake_create_combo_instance(_provider, _runtime_state_arg, _combo_name):
        calls["create_instance"] += 1
        return {
            "instance_id": "i-neuro-new",
            "status": "running",
            "actual_status": "running",
            "gpu_name": "A100_PCIE",
            "public_ipaddr": "34.1.1.1",
            "ports": {
                "8080/tcp": [{"HostPort": "32080"}],
                "8081/tcp": [{"HostPort": "32081"}],
                "8082/tcp": [{"HostPort": "32082"}],
                "9000/tcp": [{"HostPort": "39000"}],
                "9001/tcp": [{"HostPort": "39001"}],
                "7999/tcp": [{"HostPort": "37999"}],
            },
            "label": "ai-orch:neuroflow",
        }

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "_discover_combo_names",
        lambda *_a, **_k: ["neuroflow", "reasoning_80gb"],
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(restart_transition_timeout_seconds=1),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr(cli, "_create_combo_instance", _fake_create_combo_instance, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs), raising=False)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)

    exit_code = _invoke_main_safely(
        cli,
        ["wizard", "--write-runtime-file", str(runtime_file)],
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert calls["set_instance_state"] == [("i-neuro-old", "running")]
    assert calls["destroy_instance"] == ["i-neuro-old"]
    assert calls["create_instance"] == 1
    assert payload["instance_id"] == "i-neuro-new"
    assert runtime_file.exists()


def test_wizard_restart_timeout_can_back_out_to_instance_selection(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    runtime_file = tmp_path / "wizard-runtime.json"
    calls = {"create_instance": 0}
    inputs = iter(["1", "1", "1", "4", "0", "1"])

    _install_fake_clock(cli, monkeypatch)

    class _FakeProvider:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        def list_instances(self):
            return [
                {
                    "instance_id": "i-neuro-old",
                    "status": "exited",
                    "actual_status": "exited",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": None,
                    "label": "ai-orch:neuroflow",
                }
            ]

        def poll_instance(self, instance_id):
            if instance_id == "i-neuro-old":
                return {
                    "instance_id": "i-neuro-old",
                    "status": "scheduling",
                    "actual_status": "scheduling",
                    "gpu_name": "A100_PCIE",
                    "public_ipaddr": None,
                    "ports": {},
                    "label": "ai-orch:neuroflow",
                }
            return {
                "instance_id": "i-neuro-new",
                "status": "running",
                "actual_status": "running",
                "gpu_name": "A100_PCIE",
                "dph": 0.95,
                "public_ipaddr": "34.1.1.1",
                "ports": {
                    "8080/tcp": [{"HostPort": "32080"}],
                    "8081/tcp": [{"HostPort": "32081"}],
                    "8082/tcp": [{"HostPort": "32082"}],
                    "9000/tcp": [{"HostPort": "39000"}],
                    "9001/tcp": [{"HostPort": "39001"}],
                    "7999/tcp": [{"HostPort": "37999"}],
                },
                "label": "ai-orch:neuroflow",
            }

        def set_instance_state(self, *_args, **_kwargs):
            return {"status": "ok"}

    def _fake_create_combo_instance(_provider, _runtime_state_arg, _combo_name):
        calls["create_instance"] += 1
        return {
            "instance_id": "i-neuro-new",
            "status": "running",
            "actual_status": "running",
            "gpu_name": "A100_PCIE",
            "public_ipaddr": "34.1.1.1",
            "ports": {
                "8080/tcp": [{"HostPort": "32080"}],
                "8081/tcp": [{"HostPort": "32081"}],
                "8082/tcp": [{"HostPort": "32082"}],
                "9000/tcp": [{"HostPort": "39000"}],
                "9001/tcp": [{"HostPort": "39001"}],
                "7999/tcp": [{"HostPort": "37999"}],
            },
            "label": "ai-orch:neuroflow",
        }

    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(
        cli,
        "_discover_combo_names",
        lambda *_a, **_k: ["neuroflow", "reasoning_80gb"],
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "resolve_runtime_state_for_combo",
        lambda *_a, **_k: _runtime_state(restart_transition_timeout_seconds=1),
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "_fetch_combo_control_health",
        lambda *_a, **_k: _healthy_control_payload(),
        raising=False,
    )
    monkeypatch.setattr(cli, "_create_combo_instance", _fake_create_combo_instance, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs), raising=False)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)

    exit_code = _invoke_main_safely(
        cli,
        ["wizard", "--write-runtime-file", str(runtime_file)],
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert calls["create_instance"] == 1
    assert payload["instance_id"] == "i-neuro-new"
    assert runtime_file.exists()
