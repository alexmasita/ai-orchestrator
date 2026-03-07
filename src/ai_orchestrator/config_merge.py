from __future__ import annotations

from copy import deepcopy
from typing import Any


def _merge_values(existing: Any, override: Any, path: str) -> Any:
    if isinstance(existing, dict) and isinstance(override, dict):
        return _merge_dicts(existing, override, path)
    if isinstance(existing, dict) != isinstance(override, dict):
        raise TypeError(f"Type conflict at {path}")
    if isinstance(override, list):
        return deepcopy(override)
    return deepcopy(override)


def _merge_dicts(base: dict[str, Any], override: dict[str, Any], path: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    all_keys = sorted(set(base.keys()) | set(override.keys()))
    for key in all_keys:
        key_path = f"{path}.{key}" if path else str(key)
        if key in override and key in base:
            merged[key] = _merge_values(base[key], override[key], key_path)
        elif key in override:
            merged[key] = deepcopy(override[key])
        else:
            merged[key] = deepcopy(base[key])
    return merged


def merge_config_layers(
    base_config: dict[str, Any] | None,
    combo_config: dict[str, Any] | None,
    cli_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    base = dict(base_config or {})
    combo = dict(combo_config or {})
    cli = dict(cli_overrides or {})

    merged = _merge_dicts(base, combo, "")
    return _merge_dicts(merged, cli, "")
