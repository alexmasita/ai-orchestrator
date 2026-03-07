import importlib


SCRIPT_MODULE = "ai_orchestrator.runtime.script"


def _load_script_module():
    return importlib.import_module(SCRIPT_MODULE)


def _sample_script():
    return "#!/usr/bin/env bash\nset -e\necho boot\n"


def test_runtime_script_module_import_path():
    module = _load_script_module()
    assert module.__name__ == SCRIPT_MODULE


def test_render_bootstrap_script_exists():
    module = _load_script_module()
    assert hasattr(module, "render_bootstrap_script")
    assert callable(module.render_bootstrap_script)


def test_render_bootstrap_script_returns_str():
    module = _load_script_module()
    rendered = module.render_bootstrap_script(_sample_script(), {"A": "1"})
    assert isinstance(rendered, str)


def test_render_bootstrap_script_preserves_shebang():
    module = _load_script_module()
    rendered = module.render_bootstrap_script(_sample_script(), {"A": "1"})
    assert rendered.startswith("#!/usr/bin/env bash")


def test_render_bootstrap_script_injects_env_keys_in_sorted_order():
    module = _load_script_module()
    rendered = module.render_bootstrap_script(_sample_script(), {"Z_VAR": "z", "A_VAR": "a"})
    assert rendered.find("A_VAR") < rendered.find("Z_VAR")


def test_render_bootstrap_script_no_secret_leak():
    module = _load_script_module()
    secret = "sk_test_SUPER_SECRET"
    rendered = module.render_bootstrap_script(_sample_script(), {"VAST_API_KEY": secret, "A": "1"})
    assert secret not in rendered
    assert "VAST_API_KEY=" not in rendered


def test_render_bootstrap_script_normalizes_newlines():
    module = _load_script_module()
    rendered = module.render_bootstrap_script(
        "#!/usr/bin/env bash\r\nset -e\r\necho boot\r\n",
        {"A": "1"},
    )
    assert "\r\n" not in rendered


def test_render_bootstrap_script_is_deterministic_for_identical_inputs():
    module = _load_script_module()
    first = module.render_bootstrap_script(_sample_script(), {"A": "1", "B": "2"})
    second = module.render_bootstrap_script(_sample_script(), {"A": "1", "B": "2"})
    assert first == second
