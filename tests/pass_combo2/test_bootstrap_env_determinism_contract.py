from __future__ import annotations

import importlib
import re
from pathlib import Path


def _load_runtime_script_module():
    try:
        return importlib.import_module("ai_orchestrator.runtime.script")
    except ModuleNotFoundError:
        return None


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _extract_env_keys(env_lines: list[str]) -> list[str]:
    keys: list[str] = []
    for line in env_lines:
        match = re.match(r"^export\s+([^=]+)=", line)
        assert match is not None, "Expected env injection lines to be shell exports"
        keys.append(match.group(1))
    return keys


def test_bootstrap_env_injection_order_deterministic():
    runtime_script = _load_runtime_script_module()
    assert runtime_script is not None, "Expected ai_orchestrator.runtime.script module"
    assert hasattr(
        runtime_script, "render_bootstrap_script"
    ), "Expected render_bootstrap_script(script, env) contract"

    bootstrap_path = Path("combos") / "reasoning_80gb" / "bootstrap.sh"
    assert bootstrap_path.is_file(), "Expected combos/reasoning_80gb/bootstrap.sh asset"
    original_script = bootstrap_path.read_text(encoding="utf-8")
    normalized_original = _normalize_newlines(original_script)

    env = {
        "ZZZ": "3",
        "AAA": "1",
        1: "numeric-key",
        "1": "string-key",
    }

    rendered_first = runtime_script.render_bootstrap_script(original_script, env)
    rendered_second = runtime_script.render_bootstrap_script(original_script, env)

    assert isinstance(rendered_first, str)
    assert rendered_first.encode("utf-8") == rendered_second.encode(
        "utf-8"
    ), "Expected deterministic byte-identical env injection across repeated calls"

    rendered_lines = rendered_first.splitlines()
    original_lines = normalized_original.splitlines()
    assert len(original_lines) >= 2, "Expected bootstrap body with at least shebang + one body line"
    first_body_line = original_lines[1]
    assert first_body_line in rendered_lines, "Expected original bootstrap body to be present after injection"
    body_start_idx = rendered_lines.index(first_body_line)

    env_lines = [line for line in rendered_lines[1:body_start_idx] if line.startswith("export ")]
    assert env_lines, "Expected environment block injected ahead of bootstrap body"

    env_keys = _extract_env_keys(env_lines)
    assert env_keys == sorted(
        env_keys
    ), "Expected injected env keys to be sorted deterministically"
    assert len(env_keys) == len(
        set(env_keys)
    ), "Expected no duplicate injected env keys after normalization"

    rendered_body = "\n".join(rendered_lines[body_start_idx:])
    original_body = "\n".join(original_lines[1:])
    assert rendered_body.encode("utf-8") == original_body.encode(
        "utf-8"
    ), "Expected bootstrap body bytes to remain unchanged after env injection"

