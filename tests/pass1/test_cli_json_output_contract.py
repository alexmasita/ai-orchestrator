from __future__ import annotations

import importlib
import json


def _load_cli_module():
    try:
        return importlib.import_module("ai_orchestrator.cli")
    except ModuleNotFoundError:
        return None


def test_cli_json_output_key_order():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "format_json_output"), "Expected format_json_output(payload) contract"

    payload = {
        "whisper_url": "http://1.2.3.4:9000",
        "instance_id": "abc123",
        "deepseek_url": "http://1.2.3.4:8080",
        "gpu_type": "A100",
        "snapshot_version": "v1",
        "cost_per_hour": 1.2,
        "idle_timeout": 1800,
    }
    output = cli.format_json_output(payload)

    parsed = json.loads(output)
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_cli_json_output_canonical_serialization():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "format_json_output"), "Expected format_json_output(payload) contract"

    payload = {
        "instance_id": "abc123",
        "gpu_type": "A100",
        "cost_per_hour": 1.2,
        "idle_timeout": 1800,
        "snapshot_version": "v1",
        "deepseek_url": "http://1.2.3.4:8080",
        "whisper_url": "http://1.2.3.4:9000",
    }
    first = cli.format_json_output(payload)
    second = cli.format_json_output(payload)
    assert first == second
    assert first == json.dumps(json.loads(first), sort_keys=True)


def test_cli_list_output_deterministic_order():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "format_list_output"), "Expected format_list_output(instances) contract"

    instances = [
        {"instance_id": "3", "status": "running"},
        {"instance_id": "1", "status": "running"},
        {"instance_id": "2", "status": "stopped"},
    ]
    first = json.loads(cli.format_list_output(instances))
    second = json.loads(cli.format_list_output(instances))

    first_ids = [item["instance_id"] for item in first["instances"]]
    second_ids = [item["instance_id"] for item in second["instances"]]
    assert first_ids == ["1", "2", "3"]
    assert first_ids == second_ids
