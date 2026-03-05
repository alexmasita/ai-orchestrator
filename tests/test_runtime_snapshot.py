import importlib

import pytest


SNAPSHOT_MODULE = "ai_orchestrator.runtime.snapshot"


def _load_snapshot_module():
    return importlib.import_module(SNAPSHOT_MODULE)


def test_snapshot_module_import_path():
    module = _load_snapshot_module()
    assert module.__name__ == SNAPSHOT_MODULE


def test_get_snapshot_version_exists():
    module = _load_snapshot_module()
    assert hasattr(module, "get_snapshot_version")
    assert callable(module.get_snapshot_version)


def test_get_snapshot_version_returns_config_value():
    module = _load_snapshot_module()
    config = {"snapshot_version": "snap-v1"}
    assert module.get_snapshot_version(config) == "snap-v1"


def test_get_snapshot_version_missing_key_raises_key_error():
    module = _load_snapshot_module()
    with pytest.raises(KeyError):
        module.get_snapshot_version({})


def test_get_snapshot_version_non_string_raises_type_error():
    module = _load_snapshot_module()
    with pytest.raises(TypeError):
        module.get_snapshot_version({"snapshot_version": 123})


def test_get_snapshot_version_is_deterministic():
    module = _load_snapshot_module()
    config = {"snapshot_version": "snap-v1"}
    first = module.get_snapshot_version(config)
    second = module.get_snapshot_version(config)
    assert first == second
