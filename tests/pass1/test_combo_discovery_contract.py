from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _load_combo_loader():
    try:
        return importlib.import_module("ai_orchestrator.combos.loader")
    except ModuleNotFoundError:
        return None


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_combo_dir(
    combos_root: Path,
    directory_name: str,
    combo_name: str,
    *,
    include_combo_yaml: bool = True,
    include_bootstrap_script: bool = True,
    include_config_yaml: bool = True,
) -> None:
    combo_dir = combos_root / directory_name
    combo_dir.mkdir(parents=True, exist_ok=True)

    if include_combo_yaml:
        _write_file(
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

    if include_bootstrap_script:
        _write_file(
            combo_dir / "bootstrap.sh",
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -e",
                    "echo ready",
                ]
            )
            + "\n",
        )

    if include_config_yaml:
        _write_file(combo_dir / "config.yaml", "snapshot_version: v1\n")


def test_combo_discovery_sorted_filesystem_entries(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "discover_combos"), "Expected discover_combos(combos_root) contract"

    combos_root = tmp_path / "combos"
    _create_combo_dir(combos_root, "zeta", "zeta")
    _create_combo_dir(combos_root, "alpha", "alpha")
    _create_combo_dir(combos_root, "beta", "beta")

    discovered = loader.discover_combos(combos_root)
    assert discovered == ["alpha", "beta", "zeta"]


def test_combo_discovery_ignores_non_combo_directories(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "discover_combos"), "Expected discover_combos(combos_root) contract"

    combos_root = tmp_path / "combos"
    _create_combo_dir(combos_root, "alpha", "alpha")
    (combos_root / "__pycache__").mkdir(parents=True, exist_ok=True)
    (combos_root / "docs").mkdir(parents=True, exist_ok=True)
    _write_file(combos_root / "docs" / "README.md", "# docs\n")
    _write_file(combos_root / "notes.txt", "ignore me\n")

    discovered = loader.discover_combos(combos_root)
    assert discovered == ["alpha"]


def test_combo_discovery_missing_required_files(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "discover_combos"), "Expected discover_combos(combos_root) contract"

    combos_root = tmp_path / "combos"
    _create_combo_dir(
        combos_root,
        "broken",
        "broken",
        include_bootstrap_script=False,
    )

    with pytest.raises(ValueError, match=r"Missing required combo files: bootstrap\.sh"):
        loader.discover_combos(combos_root)


def test_combo_discovery_duplicate_combo_names(tmp_path):
    loader = _load_combo_loader()
    assert loader is not None, "Expected ai_orchestrator.combos.loader module"
    assert hasattr(loader, "discover_combos"), "Expected discover_combos(combos_root) contract"

    combos_root = tmp_path / "combos"
    _create_combo_dir(combos_root, "a", "duplicate_name")
    _create_combo_dir(combos_root, "b", "duplicate_name")

    with pytest.raises(ValueError, match=r"Duplicate combo name: duplicate_name"):
        loader.discover_combos(combos_root)
