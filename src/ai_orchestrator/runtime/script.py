from __future__ import annotations

import re

_SECRET_KEY_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD")
_ASSIGNMENT_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=")


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _is_secret_key(name: str) -> bool:
    upper_name = name.upper()
    return any(marker in upper_name for marker in _SECRET_KEY_MARKERS)


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _existing_assignment_names(script: str) -> set[str]:
    names: set[str] = set()
    for line in script.split("\n"):
        match = _ASSIGNMENT_RE.match(line)
        if match is not None:
            names.add(match.group(1))
    return names


def render_bootstrap_script(script: str, env: dict[str, str]) -> str:
    if not isinstance(script, str):
        raise TypeError("script must be a str")
    if not isinstance(env, dict):
        raise TypeError("env must be a dict")

    normalized_script = _normalize_newlines(script)
    existing_assignments = _existing_assignment_names(normalized_script)

    normalized_env: dict[str, str] = {}
    for raw_key, raw_value in env.items():
        key = str(raw_key)
        normalized_env[key] = str(raw_value)

    env_lines: list[str] = []
    for key in sorted(normalized_env.keys()):
        if key in existing_assignments:
            continue
        if _is_secret_key(key):
            continue
        value = normalized_env[key]
        env_lines.append(f"export {key}={_shell_quote(value)}")

    if normalized_script.startswith("#!"):
        first_line, sep, remaining = normalized_script.partition("\n")
        if sep == "":
            body_lines: list[str] = []
        else:
            body_lines = remaining.split("\n")
        output_lines = [first_line, *env_lines, *body_lines]
        return "\n".join(output_lines)

    if not env_lines:
        return normalized_script
    return "\n".join([*env_lines, normalized_script])
