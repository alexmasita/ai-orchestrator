from __future__ import annotations

import importlib
from pathlib import Path


def _load_snapshot_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.snapshot_manager")
    except ModuleNotFoundError:
        return None


def _load_combo_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def test_snapshot_namespace_deterministic():
    snapshot_manager = _load_snapshot_manager_module()
    assert snapshot_manager is not None, "Expected ai_orchestrator.core.snapshot_manager module"
    assert hasattr(
        snapshot_manager, "compute_snapshot_namespace"
    ), "Expected compute_snapshot_namespace(combo_name, snapshot_version) contract"

    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    combo_name = "reasoning_80gb"
    snapshot_version = "v1-80gb"

    direct_a = snapshot_manager.compute_snapshot_namespace(
        combo_name=combo_name,
        snapshot_version=snapshot_version,
    )
    direct_b = snapshot_manager.compute_snapshot_namespace(
        combo_name=combo_name,
        snapshot_version=snapshot_version,
    )
    assert direct_a == direct_b, "Expected identical inputs to produce identical snapshot namespace"
    assert (
        direct_a == "v1-80gb_reasoning_80gb"
    ), "Expected namespace format '<snapshot_version>_<combo_name>'"

    base_config_a = {
        "snapshot_version": snapshot_version,
        "min_disk_gb": 250,
        "max_dph": 2.5,
        "gpu": {"min_vram_gb": 79},
    }
    state_a = combo_manager.resolve_runtime_state_for_combo(
        combos_root=Path("combos"),
        combo_name=combo_name,
        base_config=base_config_a,
        cli_overrides={},
    )
    assert isinstance(state_a, dict), "Expected runtime state mapping"
    assert (
        "snapshot_namespace" in state_a
    ), "Expected runtime state to expose snapshot_namespace contract"
    assert state_a["snapshot_namespace"] == direct_a

    # Unrelated runtime config changes must not alter snapshot namespace.
    base_config_b = {
        "snapshot_version": snapshot_version,
        "min_disk_gb": 500,
        "max_dph": 1.0,
        "gpu": {"min_vram_gb": 96, "preferred_models": ["H100_SXM"]},
    }
    state_b = combo_manager.resolve_runtime_state_for_combo(
        combos_root=Path("combos"),
        combo_name=combo_name,
        base_config=base_config_b,
        cli_overrides={},
    )
    assert isinstance(state_b, dict), "Expected runtime state mapping for mutated config"
    assert (
        "snapshot_namespace" in state_b
    ), "Expected runtime state to expose snapshot_namespace contract"
    assert (
        state_b["snapshot_namespace"] == direct_a
    ), "Expected namespace to be independent of disk/GPU filters and unrelated runtime config fields"

