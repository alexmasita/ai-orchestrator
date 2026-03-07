from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    "provider": "",
    "active_instance": "",
    "instances": [],
}


def serialize_state(state: dict[str, Any]) -> str:
    return json.dumps(state, sort_keys=True)


def _write_state_temp_then_rename(path: Path, serialized_state: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(serialized_state, encoding="utf-8")
    os.replace(temp_path, path)


def write_state_atomic(path: str | Path, state: dict[str, Any]) -> None:
    state_path = Path(path)
    serialized_state = serialize_state(state)
    _write_state_temp_then_rename(state_path, serialized_state)


def load_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return dict(DEFAULT_STATE)

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_STATE)

    if not isinstance(payload, dict):
        return dict(DEFAULT_STATE)

    merged = dict(payload)
    for key, default_value in DEFAULT_STATE.items():
        merged.setdefault(key, default_value)
    return merged
