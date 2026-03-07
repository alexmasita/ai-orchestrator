from __future__ import annotations

import importlib
import json


def _load_orchestrator_module():
    try:
        return importlib.import_module("ai_orchestrator.orchestrator")
    except ModuleNotFoundError:
        return None


def _combo2_manifest():
    return {
        "name": "reasoning_80gb",
        "services": {
            "architect": {"port": 8080},
            "developer": {"port": 8081},
            "stt": {"port": 9000},
            "tts": {"port": 9001},
            "control": {"port": 7999, "health_path": "/health"},
        },
    }


def _instance_payload_with_mappings(ip_key: str):
    return {
        ip_key: "34.120.10.99",
        "ports": {
            "8080/tcp": [{"HostPort": "32080"}],
            "8081/tcp": [{"HostPort": "32081"}],
            "9000/tcp": [{"HostPort": "39000"}],
            "9001/tcp": [{"HostPort": "39001"}],
            "7999/tcp": [{"HostPort": "37999"}],
        },
    }


def test_endpoint_resolution_all_five_services_from_manifest_and_vast_mapping():
    orchestrator = _load_orchestrator_module()
    assert orchestrator is not None, "Expected ai_orchestrator.orchestrator module"
    assert hasattr(
        orchestrator, "resolve_combo_endpoints"
    ), "Expected resolve_combo_endpoints(instance_payload, combo_manifest) contract"

    resolved = orchestrator.resolve_combo_endpoints(
        _instance_payload_with_mappings("public_ipaddr"),
        _combo2_manifest(),
    )

    expected = {
        "architect_url": "http://34.120.10.99:32080",
        "developer_url": "http://34.120.10.99:32081",
        "stt_url": "http://34.120.10.99:39000",
        "tts_url": "http://34.120.10.99:39001",
        "control_url": "http://34.120.10.99:37999",
    }
    assert resolved == expected

    expected_order = [
        "architect_url",
        "developer_url",
        "stt_url",
        "tts_url",
        "control_url",
    ]
    assert list(resolved.keys()) == expected_order

    first = json.dumps(resolved, separators=(",", ":"))
    second = json.dumps(
        orchestrator.resolve_combo_endpoints(
            _instance_payload_with_mappings("public_ipaddr"),
            _combo2_manifest(),
        ),
        separators=(",", ":"),
    )
    assert first == second


def test_endpoint_resolution_accepts_public_ipaddr_or_public_ip():
    orchestrator = _load_orchestrator_module()
    assert orchestrator is not None, "Expected ai_orchestrator.orchestrator module"
    assert hasattr(
        orchestrator, "resolve_combo_endpoints"
    ), "Expected resolve_combo_endpoints(instance_payload, combo_manifest) contract"

    from_public_ipaddr = orchestrator.resolve_combo_endpoints(
        _instance_payload_with_mappings("public_ipaddr"),
        _combo2_manifest(),
    )
    from_public_ip = orchestrator.resolve_combo_endpoints(
        _instance_payload_with_mappings("public_ip"),
        _combo2_manifest(),
    )

    assert from_public_ipaddr == from_public_ip
    assert set(from_public_ip.keys()) == {
        "architect_url",
        "developer_url",
        "stt_url",
        "tts_url",
        "control_url",
    }
