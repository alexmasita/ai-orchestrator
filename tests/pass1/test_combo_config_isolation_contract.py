from __future__ import annotations

import importlib
from pathlib import Path


def _load_combo_loader():
    try:
        return importlib.import_module("ai_orchestrator.combos.loader")
    except ModuleNotFoundError:
        return None


def _load_config_merge():
    try:
        return importlib.import_module("ai_orchestrator.config_merge")
    except ModuleNotFoundError:
        return None


def _load_combo_manager():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_combo(
    combos_root: Path,
    combo_dir_name: str,
    combo_name: str,
    config_lines: list[str],
) -> Path:
    combo_dir = combos_root / combo_dir_name
    combo_dir.mkdir(parents=True, exist_ok=True)

    _write(
        combo_dir / "combo.yaml",
        "\n".join(
            [
                "schema_version: 1",
                f"name: {combo_name}",
                "provider: vast",
                "services:",
                "  architect:",
                "    port: 8080",
            ]
        )
        + "\n",
    )
    _write(
        combo_dir / "bootstrap.sh",
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -e",
                "echo boot",
            ]
        )
        + "\n",
    )
    _write(combo_dir / "config.yaml", "\n".join(config_lines) + "\n")
    return combo_dir


def test_combo_config_loaded_from_combo_directory(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    combos_root = tmp_path / "combos"
    combo_dir = _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        [
            "combo_tag: deepseek_whisper",
            "idle_timeout_seconds: 1800",
        ],
    )

    combo = loader.load_combo(combos_root, "deepseek_whisper")
    assert hasattr(combo, "combo_config"), "Expected combo_config on loaded combo definition"
    assert combo.combo_config["combo_tag"] == "deepseek_whisper"
    assert hasattr(combo, "config_path"), "Expected config_path metadata on loaded combo definition"
    assert Path(combo.config_path) == combo_dir / "config.yaml"
    assert Path(combo.config_path).parent == combo_dir


def test_combo_config_not_shared_between_combos(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "load_combo"), "Expected load_combo(combos_root, combo_name) contract"

    combos_root = tmp_path / "combos"
    _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        [
            "combo_tag: deepseek_whisper",
            "max_dph: 1.2",
        ],
    )
    _create_combo(
        combos_root,
        "reasoning_80gb",
        "reasoning_80gb",
        [
            "combo_tag: reasoning_80gb",
            "max_dph: 2.5",
        ],
    )

    first = loader.load_combo(combos_root, "deepseek_whisper")
    second = loader.load_combo(combos_root, "reasoning_80gb")

    assert first.combo_config["combo_tag"] == "deepseek_whisper"
    assert second.combo_config["combo_tag"] == "reasoning_80gb"
    assert first.combo_config["max_dph"] == 1.2
    assert second.combo_config["max_dph"] == 2.5
    assert first.combo_config is not second.combo_config


def test_combo_config_merge_isolated_per_combo():
    merge_mod = _load_config_merge()
    assert merge_mod is not None, "Expected ai_orchestrator.config_merge module"
    assert hasattr(
        merge_mod, "merge_config_layers"
    ), "Expected merge_config_layers(base_config, combo_config, cli_overrides) contract"

    base = {
        "provider": "vast",
        "limits": {"max_dph": 3.0},
    }
    deepseek_combo = {
        "combo_tag": "deepseek_whisper",
        "limits": {"max_dph": 1.2},
    }
    reasoning_combo = {
        "combo_tag": "reasoning_80gb",
        "limits": {"max_dph": 2.5},
    }
    cli = {"limits": {"max_dph": 0.9}}

    merged_a = merge_mod.merge_config_layers(base, deepseek_combo, cli)
    merged_b = merge_mod.merge_config_layers(base, reasoning_combo, cli)

    assert merged_a["combo_tag"] == "deepseek_whisper"
    assert merged_b["combo_tag"] == "reasoning_80gb"
    assert merged_a["limits"]["max_dph"] == 0.9
    assert merged_b["limits"]["max_dph"] == 0.9

    merged_a["limits"]["max_dph"] = 99
    assert merged_b["limits"]["max_dph"] == 0.9


def test_combo_switch_resets_runtime_config(tmp_path):
    combo_manager = _load_combo_manager()
    assert combo_manager is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        combo_manager, "resolve_runtime_config_for_combo"
    ), "Expected resolve_runtime_config_for_combo(combos_root, combo_name, base_config, cli_overrides) contract"

    combos_root = tmp_path / "combos"
    _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        [
            "combo_tag: deepseek_whisper",
            "deepseek_only: true",
            "idle_timeout_seconds: 1800",
        ],
    )
    _create_combo(
        combos_root,
        "reasoning_80gb",
        "reasoning_80gb",
        [
            "combo_tag: reasoning_80gb",
            "idle_timeout_seconds: 1200",
        ],
    )

    base = {"provider": "vast", "region": "global"}
    cli = {"allow_multiple": False}

    before_switch = combo_manager.resolve_runtime_config_for_combo(
        combos_root, "deepseek_whisper", base, cli
    )
    after_switch = combo_manager.resolve_runtime_config_for_combo(
        combos_root, "reasoning_80gb", base, cli
    )

    assert before_switch["combo_tag"] == "deepseek_whisper"
    assert after_switch["combo_tag"] == "reasoning_80gb"
    assert "deepseek_only" in before_switch
    assert "deepseek_only" not in after_switch
