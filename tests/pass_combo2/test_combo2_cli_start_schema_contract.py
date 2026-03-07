from __future__ import annotations

import importlib
import json


def _load_cli_module():
    try:
        return importlib.import_module("ai_orchestrator.cli")
    except ModuleNotFoundError:
        return None


def test_combo2_cli_endpoint_order_deterministic():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(
        cli, "format_json_output"
    ), "Expected format_json_output(payload) contract"

    payload = {
        "control_url": "http://1.2.3.4:32000",
        "tts_url": "http://1.2.3.4:32001",
        "stt_url": "http://1.2.3.4:32002",
        "developer_url": "http://1.2.3.4:32003",
        "architect_url": "http://1.2.3.4:32004",
        "snapshot_version": "v1-80gb",
        "idle_timeout": 1800,
        "cost_per_hour": 2.5,
        "gpu_type": "A100_SXM4",
        "instance_id": "i-123",
    }

    first = cli.format_json_output(payload)
    second = cli.format_json_output(payload)
    assert first == second
    assert "\n" not in first, "Expected single-line JSON output"

    # Contract: CLI start output uses canonical JSON helper.
    assert first == json.dumps(payload, sort_keys=True)

    parsed = json.loads(first)
    keys = list(parsed.keys())
    expected_key_order = sorted(payload.keys())
    assert keys == expected_key_order

    endpoint_keys = [key for key in keys if key.endswith("_url")]
    assert endpoint_keys == sorted(endpoint_keys)
