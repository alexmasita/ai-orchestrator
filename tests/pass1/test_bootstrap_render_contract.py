from __future__ import annotations

import importlib


def _load_runtime_script_module():
    try:
        return importlib.import_module("ai_orchestrator.runtime.script")
    except ModuleNotFoundError:
        return None


def _render(module, script: str, env: dict[str, str]) -> str:
    assert hasattr(
        module, "render_bootstrap_script"
    ), "Expected render_bootstrap_script(script, env) contract"
    return module.render_bootstrap_script(script, env)


def test_bootstrap_env_injection_sorted_keys():
    module = _load_runtime_script_module()
    assert module is not None, "Expected ai_orchestrator.runtime.script module"

    script = "#!/usr/bin/env bash\nset -e\necho boot\n"
    rendered = _render(module, script, {"Z_VAR": "z", "A_VAR": "a", "M_VAR": "m"})

    a_pos = rendered.find("A_VAR")
    m_pos = rendered.find("M_VAR")
    z_pos = rendered.find("Z_VAR")
    assert -1 not in (a_pos, m_pos, z_pos)
    assert a_pos < m_pos < z_pos


def test_bootstrap_env_injection_no_secret_leak():
    module = _load_runtime_script_module()
    assert module is not None, "Expected ai_orchestrator.runtime.script module"

    secret = "sk_test_SUPER_SECRET"
    script = "#!/usr/bin/env bash\nset -e\necho boot\n"
    rendered = _render(module, script, {"VAST_API_KEY": secret, "SAFE": "1"})

    assert secret not in rendered
    assert "VAST_API_KEY=" not in rendered


def test_bootstrap_render_byte_identical():
    module = _load_runtime_script_module()
    assert module is not None, "Expected ai_orchestrator.runtime.script module"

    script = "#!/usr/bin/env bash\nset -e\necho boot\n"
    env = {"A": "1", "B": "2"}

    first = _render(module, script, env)
    second = _render(module, script, env)
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_bootstrap_render_unix_newlines():
    module = _load_runtime_script_module()
    assert module is not None, "Expected ai_orchestrator.runtime.script module"

    script = "#!/usr/bin/env bash\r\nset -e\r\necho boot\r\n"
    rendered = _render(module, script, {"A": "1"})
    assert "\r\n" not in rendered
