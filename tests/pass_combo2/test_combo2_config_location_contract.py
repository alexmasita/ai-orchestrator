from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_combo_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_combo_fixture(combos_root: Path) -> None:
    combo_dir = combos_root / "reasoning_80gb"
    _write(
        combo_dir / "combo.yaml",
        "\n".join(
            [
                "schema_version: 1",
                "name: reasoning_80gb",
                "provider: vast",
                "services:",
                "  architect:",
                "    port: 8080",
                "  control:",
                "    port: 7999",
                "    health_path: /health",
            ]
        )
        + "\n",
    )
    _write(
        combo_dir / "bootstrap.sh",
        "\n".join(["#!/usr/bin/env bash", "set -e", "echo boot"]) + "\n",
    )
    _write(
        combo_dir / "config.yaml",
        "\n".join(
            [
                "idle_timeout_seconds: 77",
                "instance_ready_timeout_seconds: 88",
                "min_disk_gb: 111",
                "max_dph: 9.9",
                "combo_runtime_source: combo_dir",
            ]
        )
        + "\n",
    )


def test_runtime_config_not_loaded_from_combo_directory(tmp_path, monkeypatch):
    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    combos_root = tmp_path / "combos"
    configs_root = tmp_path / "configs"
    _create_combo_fixture(combos_root)
    _write(
        configs_root / "reasoning_80gb.yaml",
        "\n".join(
            [
                "idle_timeout_seconds: 1800",
                "instance_ready_timeout_seconds: 1800",
                "min_disk_gb: 250",
                "max_dph: 2.5",
                "runtime_config_source: configs_dir",
            ]
        )
        + "\n",
    )

    monkeypatch.chdir(tmp_path)

    state_a = combo_manager.resolve_runtime_state_for_combo(
        combos_root=combos_root,
        combo_name="reasoning_80gb",
        base_config={},
        cli_overrides={},
    )
    state_b = combo_manager.resolve_runtime_state_for_combo(
        combos_root=combos_root,
        combo_name="reasoning_80gb",
        base_config={},
        cli_overrides={},
    )

    runtime_config = state_a.get("runtime_config", {})
    assert isinstance(runtime_config, dict), "Expected runtime_config mapping in runtime state"

    assert runtime_config.get("runtime_config_source") == "configs_dir"
    assert runtime_config.get("idle_timeout_seconds") == 1800
    assert runtime_config.get("instance_ready_timeout_seconds") == 1800
    assert runtime_config.get("min_disk_gb") == 250
    assert runtime_config.get("max_dph") == 2.5
    assert (
        "combo_runtime_source" not in runtime_config
    ), "Expected combo directory config values to be ignored for runtime infrastructure config"

    first_canonical = json.dumps(runtime_config, sort_keys=True, separators=(",", ":"))
    second_canonical = json.dumps(
        state_b.get("runtime_config", {}), sort_keys=True, separators=(",", ":")
    )
    assert first_canonical == second_canonical

