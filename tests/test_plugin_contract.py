import importlib


BASE_MODULE = "ai_orchestrator.plugins.base"


def _load_base_module():
    return importlib.import_module(BASE_MODULE)


def test_base_module_import_path():
    module = _load_base_module()
    assert module.__name__ == BASE_MODULE


def test_model_plugin_contract_members_exist():
    module = _load_base_module()
    assert hasattr(module, "ModelPlugin")

    model_plugin = module.ModelPlugin
    required_members = [
        "name",
        "ports",
        "required_vram_gb",
        "required_disk_gb",
        "snapshot_assets",
        "runtime_env",
    ]
    for member in required_members:
        assert hasattr(model_plugin, member), f"ModelPlugin missing required member: {member}"


def test_model_plugin_contract_methods_callable():
    module = _load_base_module()
    model_plugin = module.ModelPlugin

    required_methods = [
        "required_vram_gb",
        "required_disk_gb",
        "snapshot_assets",
        "runtime_env",
    ]
    for method_name in required_methods:
        assert callable(
            getattr(model_plugin, method_name)
        ), f"ModelPlugin.{method_name} must be callable"
