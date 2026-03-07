from __future__ import annotations

import importlib


def _load_snapshot_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.snapshot_manager")
    except ModuleNotFoundError:
        return None


def test_snapshot_namespace_is_combo_scoped():
    module = _load_snapshot_manager_module()
    assert module is not None, "Expected ai_orchestrator.core.snapshot_manager module"
    assert hasattr(
        module, "compute_snapshot_namespace"
    ), "Expected compute_snapshot_namespace(combo_name, snapshot_version) contract"

    namespace = module.compute_snapshot_namespace("deepseek_whisper", "v1")
    assert namespace == "deepseek_whisperv1"
    assert "deepseek_whisper" in namespace


def test_snapshot_switch_invalidates_previous_namespace():
    module = _load_snapshot_manager_module()
    assert module is not None, "Expected ai_orchestrator.core.snapshot_manager module"
    assert hasattr(
        module, "compute_snapshot_namespace"
    ), "Expected compute_snapshot_namespace(combo_name, snapshot_version) contract"
    assert hasattr(
        module, "is_snapshot_compatible"
    ), "Expected is_snapshot_compatible(snapshot_namespace, combo_name, snapshot_version) contract"

    deepseek_ns = module.compute_snapshot_namespace("deepseek_whisper", "v1")
    reasoning_ns = module.compute_snapshot_namespace("reasoning_80gb", "v1")

    assert deepseek_ns != reasoning_ns
    assert (
        module.is_snapshot_compatible(
            snapshot_namespace=deepseek_ns,
            combo_name="reasoning_80gb",
            snapshot_version="v1",
        )
        is False
    )
