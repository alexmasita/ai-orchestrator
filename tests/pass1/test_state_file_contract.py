from __future__ import annotations

import importlib
import json


def _load_state_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.state_manager")
    except ModuleNotFoundError:
        return None


def _sample_state() -> dict:
    return {
        "provider": "vast",
        "active_instance": "8934756",
        "instances": [
            {"id": "8934756", "combo": "deepseek_whisper"},
            {"id": "8934902", "combo": "reasoning_80gb"},
        ],
    }


def test_state_file_canonical_json_order():
    module = _load_state_manager_module()
    assert module is not None, "Expected ai_orchestrator.core.state_manager module"
    assert hasattr(
        module, "serialize_state"
    ), "Expected serialize_state(state) contract with canonical key ordering"

    first = module.serialize_state(_sample_state())
    second = module.serialize_state(_sample_state())

    assert first == second
    assert first == json.dumps(json.loads(first), sort_keys=True)
    parsed = json.loads(first)
    assert set(parsed.keys()) == {"provider", "active_instance", "instances"}


def test_state_file_atomic_write(tmp_path):
    module = _load_state_manager_module()
    assert module is not None, "Expected ai_orchestrator.core.state_manager module"
    assert hasattr(
        module, "write_state_atomic"
    ), "Expected write_state_atomic(path, state) contract"

    state_path = tmp_path / ".orchestrator_state.json"
    old_state = {
        "provider": "vast",
        "active_instance": "old-instance",
        "instances": [{"id": "old-instance", "combo": "deepseek_whisper"}],
    }
    module.write_state_atomic(state_path, old_state)

    assert hasattr(
        module, "_write_state_temp_then_rename"
    ), "Expected atomic write implementation via temp-file then rename"

    new_state = _sample_state()
    module.write_state_atomic(state_path, new_state)
    loaded = json.loads(state_path.read_text(encoding="utf-8"))
    assert loaded == new_state
