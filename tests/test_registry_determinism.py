import importlib

import pytest


REGISTRY_MODULE = "ai_orchestrator.plugins.registry"


def _load_registry_module():
    return importlib.import_module(REGISTRY_MODULE)


def test_registry_module_import_path():
    module = _load_registry_module()
    assert module.__name__ == REGISTRY_MODULE


def test_registry_exports_required_functions():
    module = _load_registry_module()
    required_functions = [
        "list_plugin_names",
        "get_plugin_registry",
        "get_plugin_by_name",
    ]
    for function_name in required_functions:
        assert hasattr(module, function_name), f"Missing required function: {function_name}"
        assert callable(getattr(module, function_name)), f"{function_name} must be callable"


def test_list_plugin_names_are_sorted():
    module = _load_registry_module()
    names = module.list_plugin_names()
    assert names == sorted(names)


def test_list_plugin_names_repeated_calls_are_identical():
    module = _load_registry_module()
    first = module.list_plugin_names()
    second = module.list_plugin_names()
    third = module.list_plugin_names()
    assert first == second == third


def test_registry_order_repeated_calls_are_identical():
    module = _load_registry_module()
    first = list(module.get_plugin_registry().keys())
    second = list(module.get_plugin_registry().keys())
    third = list(module.get_plugin_registry().keys())
    assert first == second == third


def test_modifying_returned_registry_does_not_affect_future_calls():
    module = _load_registry_module()
    registry = module.get_plugin_registry()
    sentinel_name = "__fake_plugin__"

    try:
        registry[sentinel_name] = object()
    except TypeError:
        pass

    fresh_registry = module.get_plugin_registry()
    assert sentinel_name not in fresh_registry


def test_get_plugin_by_name_unknown_raises_key_error():
    module = _load_registry_module()
    with pytest.raises(KeyError):
        module.get_plugin_by_name("__missing_plugin__")
