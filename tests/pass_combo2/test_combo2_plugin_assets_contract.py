from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_combo_loader_module():
    try:
        return importlib.import_module("ai_orchestrator.combos.loader")
    except ModuleNotFoundError:
        return None


def _load_service_registry_module():
    try:
        return importlib.import_module("ai_orchestrator.core.service_registry")
    except ModuleNotFoundError:
        return None


def _combo_manifest_path() -> Path:
    return Path("combos") / "reasoning_80gb" / "combo.yaml"


def _combo_bootstrap_path() -> Path:
    return Path("combos") / "reasoning_80gb" / "bootstrap.sh"


def test_service_registry_order_deterministic():
    loader = _load_combo_loader_module()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    service_registry_module = _load_service_registry_module()
    assert (
        service_registry_module is not None
    ), "Expected ai_orchestrator.core.service_registry module"
    assert hasattr(
        service_registry_module, "ServiceRegistry"
    ), "Expected ServiceRegistry contract"
    assert hasattr(
        service_registry_module.ServiceRegistry, "from_combo_manifest"
    ), "Expected ServiceRegistry.from_combo_manifest(manifest) contract"

    manifest_path = _combo_manifest_path()
    assert manifest_path.is_file(), "Expected combos/reasoning_80gb/combo.yaml asset"

    first_combo = loader.load_combo(Path("combos"), "reasoning_80gb")
    second_combo = loader.load_combo(Path("combos"), "reasoning_80gb")

    first_registry = service_registry_module.ServiceRegistry.from_combo_manifest(
        first_combo.combo_manifest
    )
    second_registry = service_registry_module.ServiceRegistry.from_combo_manifest(
        second_combo.combo_manifest
    )

    first_order = first_registry.service_names()
    second_order = second_registry.service_names()

    assert first_order == second_order
    manifest_order = list(first_combo.combo_manifest.get("services", {}).keys())
    assert first_order == sorted(first_order) or first_order == manifest_order

    first_canonical = json.dumps(first_order)
    second_canonical = json.dumps(second_order)
    assert first_canonical == second_canonical


def test_combo2_manifest_requires_control_service():
    loader = _load_combo_loader_module()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    manifest_path = _combo_manifest_path()
    assert manifest_path.is_file(), "Expected combos/reasoning_80gb/combo.yaml asset"

    combo = loader.load_combo(Path("combos"), "reasoning_80gb")
    services = combo.combo_manifest.get("services")
    assert isinstance(services, dict), "Expected services mapping in combo.yaml"

    assert "control" in services, "Combo manifest must define control service"
    control = services["control"]
    assert isinstance(control, dict), "Control service config must be a mapping"

    assert "port" in control, "Control service must define port"
    control_port = control["port"]
    assert isinstance(control_port, int) and not isinstance(
        control_port, bool
    ), "Control service port must be numeric"
    assert control_port == 7999, "Control service must use port 7999"

    assert "health_path" in control, "Control service must define health path"
    health_path = control["health_path"]
    assert isinstance(health_path, str) and health_path.startswith(
        "/"
    ), "Control service health path must be a valid HTTP path"


def test_combo2_bootstrap_not_empty():
    bootstrap_path = _combo_bootstrap_path()
    assert bootstrap_path.is_file(), "Expected combos/reasoning_80gb/bootstrap.sh asset"

    content = bootstrap_path.read_text(encoding="utf-8")
    assert content.strip() != "", "bootstrap.sh must not be empty"


def test_combo2_control_service_required():
    loader = _load_combo_loader_module()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    manifest_path = _combo_manifest_path()
    assert manifest_path.is_file(), "Expected combos/reasoning_80gb/combo.yaml asset"

    combo = loader.load_combo(Path("combos"), "reasoning_80gb")
    services = combo.combo_manifest.get("services")
    assert isinstance(services, dict), "Expected services mapping in combo.yaml"
    assert "control" in services, 'Combo manifest must define a "control" service'

    control = services["control"]
    assert isinstance(control, dict), "Control service config must be a mapping"
    assert "port" in control, "Control service must expose a port"
