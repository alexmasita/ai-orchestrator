from __future__ import annotations

import importlib


def _load_snapshot_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.snapshot_manager")
    except ModuleNotFoundError:
        return None


def test_combo2_snapshot_namespace_combo_scoped():
    snapshot_manager = _load_snapshot_manager_module()
    assert snapshot_manager is not None, "Expected ai_orchestrator.core.snapshot_manager module"
    assert hasattr(
        snapshot_manager, "compute_snapshot_namespace"
    ), "Expected compute_snapshot_namespace(combo_name, snapshot_version) contract"

    namespace = snapshot_manager.compute_snapshot_namespace(
        combo_name="reasoning_80gb",
        snapshot_version="v1-80gb",
    )
    assert namespace == "v1-80gb_reasoning_80gb"
