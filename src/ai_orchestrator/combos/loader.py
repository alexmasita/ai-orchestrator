from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REQUIRED_COMBO_FILES = ("combo.yaml", "bootstrap.sh")


@dataclass
class ComboDefinition:
    name: str
    provider: str
    services: dict[str, Any]
    combo_manifest: dict[str, Any]
    bootstrap_script: str
    combo_config: dict[str, Any]
    combo_path: str
    combo_yaml_path: str
    bootstrap_path: str
    config_path: str


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object in {path.name}")
    return dict(data)


def _missing_required_files(combo_dir: Path) -> list[str]:
    missing: list[str] = []
    for file_name in _REQUIRED_COMBO_FILES:
        if not (combo_dir / file_name).is_file():
            missing.append(file_name)
    return missing


def _combo_name_from_manifest(manifest: dict[str, Any]) -> str:
    combo_name = manifest.get("name")
    if not isinstance(combo_name, str) or combo_name.strip() == "":
        raise ValueError("combo.yaml must include a non-empty name")
    return combo_name


def _discover_combo_map(combos_root: Path) -> dict[str, Path]:
    combo_map: dict[str, Path] = {}
    if not combos_root.exists():
        return combo_map

    for entry in sorted(combos_root.iterdir(), key=lambda item: item.name):
        if not entry.is_dir():
            continue
        combo_yaml = entry / "combo.yaml"
        if not combo_yaml.is_file():
            continue

        missing_files = _missing_required_files(entry)
        if missing_files:
            raise ValueError(f"Missing required combo files: {', '.join(missing_files)}")

        manifest = _load_yaml_dict(combo_yaml)
        combo_name = _combo_name_from_manifest(manifest)
        if combo_name in combo_map:
            raise ValueError(f"Duplicate combo name: {combo_name}")
        combo_map[combo_name] = entry

    return combo_map


def discover_combos(combos_root: str | Path) -> list[str]:
    combo_map = _discover_combo_map(Path(combos_root))
    return sorted(combo_map.keys())


def load_combo(combos_root: str | Path, combo_name: str) -> ComboDefinition:
    root = Path(combos_root)
    combo_map = _discover_combo_map(root)
    combo_dir = combo_map.get(combo_name)
    if combo_dir is None:
        raise ValueError(f"Combo not found: {combo_name}")

    combo_yaml_path = combo_dir / "combo.yaml"
    bootstrap_path = combo_dir / "bootstrap.sh"
    config_path = combo_dir / "config.yaml"

    manifest = _load_yaml_dict(combo_yaml_path)
    loaded_name = _combo_name_from_manifest(manifest)
    provider = manifest.get("provider", "")
    services = manifest.get("services", {})
    if config_path.is_file():
        combo_config = _load_yaml_dict(config_path)
    else:
        combo_config = {}
    bootstrap_script = bootstrap_path.read_bytes().decode("utf-8")

    return ComboDefinition(
        name=loaded_name,
        provider=str(provider),
        services=dict(services) if isinstance(services, dict) else {},
        combo_manifest=manifest,
        bootstrap_script=bootstrap_script,
        combo_config=combo_config,
        combo_path=str(combo_dir),
        combo_yaml_path=str(combo_yaml_path),
        bootstrap_path=str(bootstrap_path),
        config_path=str(config_path),
    )
