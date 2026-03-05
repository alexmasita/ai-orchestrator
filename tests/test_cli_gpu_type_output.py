import importlib
import json


CLI_MODULE = "ai_orchestrator.cli"


def _load_cli_module():
    return importlib.import_module(CLI_MODULE)


def _patch_cli_pipeline(monkeypatch, cli, raw_result):
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path: {
            "vast_api_key": "k-test",
            "vast_api_url": "https://vast.example/api",
            "snapshot_version": "v1",
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
    monkeypatch.setattr(cli, "run_orchestration", lambda *args, **kwargs: raw_result, raising=False)


def test_cli_main_exists_and_callable():
    cli = _load_cli_module()
    assert hasattr(cli, "main")
    assert callable(cli.main)


def test_cli_maps_provider_gpu_fields_to_output_json(monkeypatch, capsys):
    cli = _load_cli_module()
    raw_result = {
        "instance_id": "abc123",
        "gpu_name": "RTX_4090",
        "dph": 0.72,
        "deepseek_url": "http://1.2.3.4:8080",
        "whisper_url": "http://1.2.3.4:9000",
        "idle_timeout": 1800,
        "snapshot_version": "v1",
    }
    _patch_cli_pipeline(monkeypatch, cli, raw_result)

    exit_code = cli.main(
        ["start", "--config", "x.yaml", "--models", "deepseek_llamacpp", "whisper"]
    )
    assert exit_code == 0

    output = json.loads(capsys.readouterr().out)
    assert output["gpu_type"] == "RTX_4090"
    assert output["cost_per_hour"] == 0.72
    assert "instance_id" in output
    assert "gpu_type" in output
    assert "cost_per_hour" in output
    assert "deepseek_url" in output
    assert "whisper_url" in output
    assert "gpu_name" not in output
    assert "dph" not in output
    keys = list(output.keys())
    assert keys == sorted(keys)


def test_cli_gpu_output_is_deterministic(monkeypatch, capsys):
    cli = _load_cli_module()
    raw_result = {
        "instance_id": "abc123",
        "gpu_name": "RTX_4090",
        "dph": 0.72,
        "deepseek_url": "http://1.2.3.4:8080",
        "whisper_url": "http://1.2.3.4:9000",
        "idle_timeout": 1800,
        "snapshot_version": "v1",
    }
    _patch_cli_pipeline(monkeypatch, cli, raw_result)

    _ = cli.main(["start", "--config", "x.yaml", "--models", "deepseek_llamacpp", "whisper"])
    first = capsys.readouterr().out.strip()
    first_parsed = json.loads(first)

    _ = cli.main(["start", "--config", "x.yaml", "--models", "deepseek_llamacpp", "whisper"])
    second = capsys.readouterr().out.strip()
    second_parsed = json.loads(second)

    assert first == second
    assert first_parsed == second_parsed
    assert first_parsed["gpu_type"] == "RTX_4090"
    assert first_parsed["cost_per_hour"] == 0.72
    assert "instance_id" in first_parsed
    assert "gpu_type" in first_parsed
    assert "cost_per_hour" in first_parsed
    assert "deepseek_url" in first_parsed
    assert "whisper_url" in first_parsed
    assert "gpu_name" not in first_parsed
    assert "dph" not in first_parsed
    keys = list(first_parsed.keys())
    assert keys == sorted(keys)
