from __future__ import annotations

import importlib


def _load_service_registry_module():
    try:
        return importlib.import_module("ai_orchestrator.core.service_registry")
    except ModuleNotFoundError:
        return None


def _registry_from_manifest(module, manifest: dict):
    assert hasattr(module, "ServiceRegistry"), "Expected ServiceRegistry contract"
    service_registry = module.ServiceRegistry
    assert hasattr(
        service_registry, "from_combo_manifest"
    ), "Expected ServiceRegistry.from_combo_manifest(manifest) contract"
    return service_registry.from_combo_manifest(manifest)


def _sample_manifest() -> dict:
    return {
        "name": "deepseek_whisper",
        "provider": "vast",
        "services": {
            "architect": {"port": 8080, "health_path": "/health"},
            "developer": {"port": 8081, "health_path": "/health"},
            "stt": {"port": 9000, "health_path": "/health"},
        },
    }


def test_service_registry_health_partial_failure():
    module = _load_service_registry_module()
    assert module is not None, "Expected ai_orchestrator.core.service_registry module"

    registry = _registry_from_manifest(module, _sample_manifest())
    assert hasattr(registry, "aggregate_health"), "Expected aggregate_health(results) contract"

    result = registry.aggregate_health(
        {
            "architect": {"status": "up"},
            "developer": {"status": "down"},
            "stt": {"status": "up"},
        }
    )
    assert result["overall_status"] == "degraded"
    assert result["down_services"] == ["developer"]


def test_service_registry_health_all_up():
    module = _load_service_registry_module()
    assert module is not None, "Expected ai_orchestrator.core.service_registry module"

    registry = _registry_from_manifest(module, _sample_manifest())
    result = registry.aggregate_health(
        {
            "architect": {"status": "up"},
            "developer": {"status": "up"},
            "stt": {"status": "up"},
        }
    )
    assert result["overall_status"] == "up"
    assert result["down_services"] == []


def test_service_registry_health_all_down():
    module = _load_service_registry_module()
    assert module is not None, "Expected ai_orchestrator.core.service_registry module"

    registry = _registry_from_manifest(module, _sample_manifest())
    result = registry.aggregate_health(
        {
            "architect": {"status": "down"},
            "developer": {"status": "down"},
            "stt": {"status": "down"},
        }
    )
    assert result["overall_status"] == "down"
    assert result["down_services"] == ["architect", "developer", "stt"]


def test_service_registry_unknown_service_handling():
    module = _load_service_registry_module()
    assert module is not None, "Expected ai_orchestrator.core.service_registry module"

    registry = _registry_from_manifest(module, _sample_manifest())
    result = registry.aggregate_health(
        {
            "architect": {"status": "up"},
            "developer": {"status": "up"},
            "stt": {"status": "up"},
            "unknown": {"status": "down"},
        }
    )
    assert result["overall_status"] == "up"
    assert "unknown" not in result["services"]
