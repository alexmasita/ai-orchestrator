import importlib
import json
import re
from pathlib import Path

import pytest


CLI_MODULE = "ai_orchestrator.cli"
CONFIG_MODULE = "ai_orchestrator.config"


def _load_cli_module():
    return importlib.import_module(CLI_MODULE)


def _load_config_module():
    return importlib.import_module(CONFIG_MODULE)


def _write_config_file(path: Path):
    path.write_text(
        "\n".join(
            [
                "vast_api_key: key-123",
                "vast_api_url: https://vast.example/api",
                "snapshot_version: snap-v1",
                "idle_timeout_seconds: 1800",
                "min_reliability: 0.95",
                "min_inet_up_mbps: 100.0",
                "min_inet_down_mbps: 100.0",
                "allow_interruptible: true",
                "max_dph: 2.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _assert_runtime_urls(parsed: dict):
    assert re.match(r"^http://.+:8080$", parsed["deepseek_url"])
    assert re.match(r"^http://.+:9000$", parsed["whisper_url"])


def test_cli_module_import_path():
    module = _load_cli_module()
    assert module.__name__ == CLI_MODULE


def test_cli_parser_supports_start_command():
    cli = _load_cli_module()
    parser = cli.build_parser()
    args = parser.parse_args(["start", "--config", "config.yaml", "--models", "deepseek_llamacpp"])
    assert args.command == "start"


def test_cli_start_requires_config_arg():
    cli = _load_cli_module()
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["start", "--models", "deepseek_llamacpp"])
    assert exc_info.value.code != 0


def test_cli_start_requires_models_arg():
    cli = _load_cli_module()
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["start", "--config", "config.yaml"])
    assert exc_info.value.code != 0


def test_cli_execution_pipeline_calls_run_orchestration_and_prints_json(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    _ = _load_config_module()

    config_path = tmp_path / "config.yaml"
    _write_config_file(config_path)

    loaded_config = {
        "vast_api_key": "key-123",
        "vast_api_url": "https://vast.example/api",
        "snapshot_version": "snap-v1",
        "idle_timeout_seconds": 1800,
        "min_reliability": 0.95,
        "min_inet_up_mbps": 100.0,
        "min_inet_down_mbps": 100.0,
        "allow_interruptible": True,
        "max_dph": 2.0,
    }
    expected_output = {
        "instance_id": "i-123",
        "gpu_type": "A100",
        "cost_per_hour": 1.2,
        "idle_timeout": 1800,
        "snapshot_version": "snap-v1",
        "deepseek_url": "http://127.0.0.1:8080",
        "whisper_url": "http://127.0.0.1:9000",
    }
    call_log = {"run_orchestration": []}

    class _FakeSizingInput:
        def __init__(self, models, config):
            self.models = models
            self.config = config

    class _FakeProvider:
        def __init__(self, api_key, base_url):
            self.api_key = api_key
            self.base_url = base_url

    def _fake_load_config(path):
        assert path == str(config_path)
        return loaded_config

    def _fake_compute_requirements(sizing_input):
        assert sizing_input.models == ["deepseek_llamacpp"]
        assert sizing_input.config == loaded_config
        return {"vram_gb": 30, "disk_gb": 100}

    def _fake_run_orchestration(*args, **kwargs):
        call_log["run_orchestration"].append((args, kwargs))
        return expected_output

    monkeypatch.setattr(cli, "load_config", _fake_load_config, raising=False)
    monkeypatch.setattr(cli, "SizingInput", _FakeSizingInput, raising=False)
    monkeypatch.setattr(cli, "compute_requirements", _fake_compute_requirements, raising=False)
    monkeypatch.setattr(cli, "VastProvider", _FakeProvider, raising=False)
    monkeypatch.setattr(cli, "run_orchestration", _fake_run_orchestration, raising=False)
    monkeypatch.setattr(cli, "get_plugin_registry", lambda: {"deepseek": object()}, raising=False)

    exit_code = cli.main(
        ["start", "--config", str(config_path), "--models", "deepseek_llamacpp"]
    )

    captured = capsys.readouterr().out
    printed = captured.strip()
    parsed = json.loads(printed)

    assert len(call_log["run_orchestration"]) == 1
    assert set(parsed.keys()) == {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "idle_timeout",
        "snapshot_version",
        "deepseek_url",
        "whisper_url",
    }
    assert len(parsed) == 7
    _assert_runtime_urls(parsed)
    assert exit_code == 0


def test_cli_stdout_contains_json_only(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    _ = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_config_file(config_path)

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path: {
            "vast_api_key": "key-123",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "snap-v1",
            "idle_timeout_seconds": 1800,
            "min_reliability": 0.95,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 2.0,
        },
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "SizingInput",
        lambda models, config: {"models": models, "config": config},
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "compute_requirements",
        lambda _sizing_input: {"vram_gb": 30, "disk_gb": 100},
        raising=False,
    )
    monkeypatch.setattr(cli, "VastProvider", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(
        cli,
        "run_orchestration",
        lambda *args, **kwargs: {
            "instance_id": "i-123",
            "gpu_type": "A100",
            "cost_per_hour": 1.2,
            "idle_timeout": 1800,
            "snapshot_version": "snap-v1",
            "deepseek_url": "http://127.0.0.1:8080",
            "whisper_url": "http://127.0.0.1:9000",
        },
        raising=False,
    )

    _ = cli.main(["start", "--config", str(config_path), "--models", "deepseek_llamacpp"])
    stdout = capsys.readouterr().out

    assert stdout.startswith("{")
    assert stdout.rstrip().endswith("}")
    assert len(stdout.strip().splitlines()) == 1
    parsed = json.loads(stdout)
    assert set(parsed.keys()) == {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "idle_timeout",
        "snapshot_version",
        "deepseek_url",
        "whisper_url",
    }
    assert len(parsed) == 7
    _assert_runtime_urls(parsed)


def test_cli_json_output_is_deterministically_sorted(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    _ = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_config_file(config_path)

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path: {
            "vast_api_key": "key-123",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "snap-v1",
            "idle_timeout_seconds": 1800,
            "min_reliability": 0.95,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 2.0,
        },
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "SizingInput",
        lambda models, config: {"models": models, "config": config},
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "compute_requirements",
        lambda _sizing_input: {"vram_gb": 30, "disk_gb": 100},
        raising=False,
    )
    monkeypatch.setattr(cli, "VastProvider", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(
        cli,
        "run_orchestration",
        lambda *args, **kwargs: {
            "whisper_url": "http://127.0.0.1:9000",
            "snapshot_version": "snap-v1",
            "idle_timeout": 1800,
            "deepseek_url": "http://127.0.0.1:8080",
            "cost_per_hour": 1.2,
            "gpu_type": "A100",
            "instance_id": "i-123",
        },
        raising=False,
    )

    _ = cli.main(["start", "--config", str(config_path), "--models", "deepseek_llamacpp"])
    stdout = capsys.readouterr().out.strip()
    parsed = json.loads(stdout)
    assert set(parsed.keys()) == {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "idle_timeout",
        "snapshot_version",
        "deepseek_url",
        "whisper_url",
    }
    assert len(parsed) == 7
    _assert_runtime_urls(parsed)
    assert stdout == json.dumps(parsed, sort_keys=True)


def test_cli_success_exit_code_is_zero(monkeypatch, tmp_path):
    cli = _load_cli_module()
    _ = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_config_file(config_path)

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path: {
            "vast_api_key": "key-123",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "snap-v1",
            "idle_timeout_seconds": 1800,
            "min_reliability": 0.95,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 2.0,
        },
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "SizingInput",
        lambda models, config: {"models": models, "config": config},
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "compute_requirements",
        lambda _sizing_input: {"vram_gb": 30, "disk_gb": 100},
        raising=False,
    )
    monkeypatch.setattr(cli, "VastProvider", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(
        cli,
        "run_orchestration",
        lambda *args, **kwargs: {
            "instance_id": "i-123",
            "gpu_type": "A100",
            "cost_per_hour": 1.2,
            "idle_timeout": 1800,
            "snapshot_version": "snap-v1",
            "deepseek_url": "http://127.0.0.1:8080",
            "whisper_url": "http://127.0.0.1:9000",
        },
        raising=False,
    )

    exit_code = cli.main(["start", "--config", str(config_path), "--models", "deepseek_llamacpp"])
    assert exit_code == 0


def test_cli_error_exit_code_is_non_zero_when_load_config_fails(monkeypatch, tmp_path):
    cli = _load_cli_module()
    config_module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_config_file(config_path)

    def _raise_config_error(_path):
        raise config_module.ConfigError("invalid config")

    monkeypatch.setattr(cli, "load_config", _raise_config_error, raising=False)

    exit_code = cli.main(["start", "--config", str(config_path), "--models", "deepseek_llamacpp"])
    assert exit_code != 0


def test_cli_repeated_invocation_same_input_same_output(monkeypatch, tmp_path, capsys):
    cli = _load_cli_module()
    _ = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_config_file(config_path)

    output = {
        "instance_id": "i-123",
        "gpu_type": "A100",
        "cost_per_hour": 1.2,
        "idle_timeout": 1800,
        "snapshot_version": "snap-v1",
        "deepseek_url": "http://127.0.0.1:8080",
        "whisper_url": "http://127.0.0.1:9000",
    }

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path: {
            "vast_api_key": "key-123",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "snap-v1",
            "idle_timeout_seconds": 1800,
            "min_reliability": 0.95,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 2.0,
        },
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "SizingInput",
        lambda models, config: {"models": models, "config": config},
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "compute_requirements",
        lambda _sizing_input: {"vram_gb": 30, "disk_gb": 100},
        raising=False,
    )
    monkeypatch.setattr(cli, "VastProvider", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(cli, "run_orchestration", lambda *args, **kwargs: output, raising=False)

    _ = cli.main(["start", "--config", str(config_path), "--models", "deepseek_llamacpp"])
    first = capsys.readouterr().out.strip()
    first_parsed = json.loads(first)

    _ = cli.main(["start", "--config", str(config_path), "--models", "deepseek_llamacpp"])
    second = capsys.readouterr().out.strip()
    second_parsed = json.loads(second)

    assert first == second
    assert set(first_parsed.keys()) == {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "idle_timeout",
        "snapshot_version",
        "deepseek_url",
        "whisper_url",
    }
    assert len(first_parsed) == 7
    assert first_parsed == second_parsed
    _assert_runtime_urls(first_parsed)
