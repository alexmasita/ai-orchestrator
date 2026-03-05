import importlib


DEEPSEEK_MODULE = "ai_orchestrator.plugins.deepseek_llamacpp"


def _load_deepseek_module():
    return importlib.import_module(DEEPSEEK_MODULE)


def _plugin_instance():
    module = _load_deepseek_module()
    return module.DeepSeekLlamaCppPlugin()


def test_deepseek_module_import_path():
    module = _load_deepseek_module()
    assert module.__name__ == DEEPSEEK_MODULE


def test_deepseek_plugin_class_exists():
    module = _load_deepseek_module()
    assert hasattr(module, "DeepSeekLlamaCppPlugin")


def test_vram_profiles_have_exact_required_keys():
    plugin = _plugin_instance()
    profiles = plugin.vram_profiles_gb()
    assert set(profiles.keys()) == {"Q4_K_M", "Q5_K_M"}


def test_vram_profiles_values_match_required_contract():
    plugin = _plugin_instance()
    profiles = plugin.vram_profiles_gb()
    assert profiles["Q4_K_M"] == 20
    assert profiles["Q5_K_M"] == 26


def test_required_vram_equals_max_profile_value():
    plugin = _plugin_instance()
    profiles = plugin.vram_profiles_gb()
    required = plugin.required_vram_gb({"quantization": "Q4_K_M"})
    assert required == max(profiles.values())


def test_required_vram_ignores_config_variations():
    plugin = _plugin_instance()
    a = plugin.required_vram_gb({"quantization": "Q4_K_M"})
    b = plugin.required_vram_gb({"quantization": "Q5_K_M"})
    c = plugin.required_vram_gb({"quantization": "unexpected"})
    assert a == b == c


def test_required_vram_returns_26():
    plugin = _plugin_instance()
    assert plugin.required_vram_gb({"quantization": "Q4_K_M"}) == 26
