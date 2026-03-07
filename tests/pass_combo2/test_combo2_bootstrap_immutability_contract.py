from __future__ import annotations

import importlib
from pathlib import Path


def _load_runtime_script_module():
    try:
        return importlib.import_module("ai_orchestrator.runtime.script")
    except ModuleNotFoundError:
        return None


def test_bootstrap_body_immutable_except_env_injection():
    runtime_script = _load_runtime_script_module()
    assert runtime_script is not None, "Expected ai_orchestrator.runtime.script module"
    assert hasattr(
        runtime_script, "render_bootstrap_script"
    ), "Expected render_bootstrap_script(script, env) contract"

    bootstrap_path = Path("combos") / "reasoning_80gb" / "bootstrap.sh"
    assert bootstrap_path.is_file(), "Expected combos/reasoning_80gb/bootstrap.sh asset"
    original_script = bootstrap_path.read_text(encoding="utf-8")

    rendered_a = runtime_script.render_bootstrap_script(
        original_script,
        {
            "AI_ORCH_ARCHITECT_PORT": "8080",
            "AI_ORCH_CONTROL_PORT": "7999",
            "AI_ORCH_IDLE_TIMEOUT": "1800",
        },
    )
    rendered_b = runtime_script.render_bootstrap_script(
        original_script,
        {
            "AI_ORCH_ARCHITECT_PORT": "8080",
            "AI_ORCH_CONTROL_PORT": "7999",
            "AI_ORCH_IDLE_TIMEOUT": "1800",
        },
    )

    assert rendered_a.encode("utf-8") == rendered_b.encode(
        "utf-8"
    ), "Expected deterministic byte-identical bootstrap rendering"

    original_lines = original_script.splitlines()
    rendered_lines = rendered_a.splitlines()
    assert len(original_lines) >= 2, "Expected bootstrap script with shebang and body"
    assert rendered_lines[0] == original_lines[0], "Expected shebang to remain unchanged"

    first_body_line = original_lines[1]
    assert (
        first_body_line in rendered_lines
    ), "Expected original bootstrap body to remain present after env injection"
    body_start_idx = rendered_lines.index(first_body_line)

    prepended = rendered_lines[1:body_start_idx]
    assert prepended, "Expected env injection lines between shebang and body"
    assert all(
        line.startswith("export ") for line in prepended
    ), "Expected only env export lines to be prepended"

    rendered_body_lines = rendered_lines[body_start_idx:]
    original_body_lines = original_lines[1:]
    assert (
        rendered_body_lines == original_body_lines
    ), "Expected bootstrap body lines to remain byte-identical with no rewrite/reorder/delete"

