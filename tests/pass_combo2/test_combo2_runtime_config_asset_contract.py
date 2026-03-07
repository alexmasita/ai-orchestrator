from __future__ import annotations

import importlib
import inspect
from pathlib import Path


def _load_combo_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_reasoning_combo(combos_root: Path) -> None:
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
                "  developer:",
                "    port: 8081",
                "  stt:",
                "    port: 9000",
                "  tts:",
                "    port: 9001",
                "  control:",
                "    port: 7999",
                "    health_path: /health",
            ]
        )
        + "\n",
    )
    _write(
        combo_dir / "bootstrap.sh",
        "\n".join(["#!/usr/bin/env bash", "set -e", "echo combo-boot"]) + "\n",
    )
    _write(
        combo_dir / "config.yaml",
        "\n".join(
            [
                "config_source: combo_dir",
                "combo_overrides_configs: combo",
                "precedence_marker: combo",
                "min_disk_gb: 111",
            ]
        )
        + "\n",
    )


def test_combo2_runtime_config_asset_exists():
    config_asset = Path("configs") / "reasoning_80gb.yaml"
    assert config_asset.is_file(), "Expected configs/reasoning_80gb.yaml runtime config asset"


def test_combo2_runtime_loads_config_from_configs_directory(tmp_path, monkeypatch):
    combo_manager = _load_combo_manager_module()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    signature = inspect.signature(combo_manager.resolve_runtime_state_for_combo)
    assert (
        "config_path" not in signature.parameters
    ), "Runtime combo flow must not depend on legacy --config path argument"

    combos_root = tmp_path / "combos"
    _create_reasoning_combo(combos_root)

    configs_root = tmp_path / "configs"
    _write(
        configs_root / "reasoning_80gb.yaml",
        "\n".join(
            [
                "config_source: configs_dir",
                "configs_only_key: loaded_from_configs_dir",
                "combo_overrides_configs: configs",
                "precedence_marker: configs",
                "min_disk_gb: 250",
                "instance_ready_timeout_seconds: 1800",
            ]
        )
        + "\n",
    )

    # Keep cwd local so relative configs/reasoning_80gb.yaml resolution is deterministic.
    monkeypatch.chdir(tmp_path)

    runtime_state = combo_manager.resolve_runtime_state_for_combo(
        combos_root=combos_root,
        combo_name="reasoning_80gb",
        base_config={
            "precedence_marker": "base",
            "base_only_key": "from_base",
        },
        cli_overrides={
            "precedence_marker": "cli",
            "cli_only_key": "from_cli",
        },
    )

    runtime_config = runtime_state.get("runtime_config", {})
    # configs/<combo>.yaml must be loaded into runtime config.
    assert runtime_config.get("configs_only_key") == "loaded_from_configs_dir"

    # combo/config.yaml may override configs/<combo>.yaml values.
    assert runtime_config.get("config_source") == "combo_dir"
    assert runtime_config.get("combo_overrides_configs") == "combo"

    # CLI overrides remain highest precedence.
    assert runtime_config.get("precedence_marker") == "cli"
    assert runtime_config.get("cli_only_key") == "from_cli"
