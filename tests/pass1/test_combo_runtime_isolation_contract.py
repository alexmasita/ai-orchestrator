from __future__ import annotations

import importlib
import json
from pathlib import Path

import yaml


def _load_combo_manager_module():
    try:
        return importlib.import_module("ai_orchestrator.core.combo_manager")
    except ModuleNotFoundError:
        return None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_combo(
    combos_root: Path,
    dir_name: str,
    combo_name: str,
    services_yaml_lines: list[str],
    bootstrap_content: str,
    config_yaml_lines: list[str],
) -> Path:
    combo_dir = combos_root / dir_name
    combo_dir.mkdir(parents=True, exist_ok=True)

    combo_yaml_lines = [
        "schema_version: 1",
        f"name: {combo_name}",
        "provider: vast",
        "services:",
        *services_yaml_lines,
    ]
    _write(combo_dir / "combo.yaml", "\n".join(combo_yaml_lines) + "\n")
    _write(combo_dir / "bootstrap.sh", bootstrap_content)
    _write(combo_dir / "config.yaml", "\n".join(config_yaml_lines) + "\n")

    return combo_dir


def _resolve_state(
    module,
    combos_root: Path,
    combo_name: str,
    base_config: dict,
    cli_overrides: dict,
    previous_runtime_state: dict | None = None,
) -> dict:
    assert module is not None, "Expected ai_orchestrator.core.combo_manager module"
    assert hasattr(
        module, "resolve_runtime_state_for_combo"
    ), "Expected resolve_runtime_state_for_combo(combos_root, combo_name, base_config, cli_overrides, previous_runtime_state=None) contract"

    state = module.resolve_runtime_state_for_combo(
        combos_root,
        combo_name,
        base_config,
        cli_overrides,
        previous_runtime_state=previous_runtime_state,
    )
    assert isinstance(state, dict), "Expected runtime state as dict"

    required_keys = {
        "combo_name",
        "combo_manifest",
        "bootstrap_script",
        "runtime_config",
        "service_registry",
    }
    assert required_keys.issubset(state.keys()), "Missing required runtime state keys"
    assert hasattr(
        state["service_registry"], "service_names"
    ), "Expected service_registry.service_names() contract"

    return state


def _canonical_runtime_projection(state: dict) -> str:
    service_names = state["service_registry"].service_names()
    assert service_names == sorted(service_names), "Service names must be sorted deterministically"

    projection = {
        "combo_name": state["combo_name"],
        "combo_manifest": state["combo_manifest"],
        "bootstrap_script_bytes": state["bootstrap_script"].encode("utf-8").hex(),
        "runtime_config": state["runtime_config"],
        "service_names": service_names,
    }
    return json.dumps(projection, sort_keys=True, separators=(",", ":"))


def test_combo_switch_rebuilds_service_registry(tmp_path):
    module = _load_combo_manager_module()
    combos_root = tmp_path / "combos"

    _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  stt:",
            "    port: 9000",
        ],
        bootstrap_content="#!/usr/bin/env bash\nset -e\necho deepseek\n",
        config_yaml_lines=["combo_tag: deepseek_whisper"],
    )
    _create_combo(
        combos_root,
        "reasoning_80gb",
        "reasoning_80gb",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  developer:",
            "    port: 8081",
            "  tts:",
            "    port: 9001",
        ],
        bootstrap_content="#!/usr/bin/env bash\nset -e\necho reasoning\n",
        config_yaml_lines=["combo_tag: reasoning_80gb"],
    )

    base = {"provider": "vast"}
    cli = {"allow_multiple": False}

    state_a = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a,
    )

    registry_a = state_a["service_registry"]
    registry_b = state_b["service_registry"]
    assert registry_a is not registry_b

    services_b = registry_b.service_names()
    assert services_b == sorted(services_b)
    assert services_b == ["architect", "developer", "tts"]
    assert "stt" not in services_b

    state_a_repeat = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b_repeat = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a_repeat,
    )
    assert state_b_repeat["service_registry"].service_names() == services_b


def test_combo_switch_reloads_combo_manifest(tmp_path):
    module = _load_combo_manager_module()
    combos_root = tmp_path / "combos"

    deepseek_dir = _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  stt:",
            "    port: 9000",
        ],
        bootstrap_content="#!/usr/bin/env bash\nset -e\necho deepseek\n",
        config_yaml_lines=["combo_tag: deepseek_whisper"],
    )
    reasoning_dir = _create_combo(
        combos_root,
        "reasoning_80gb",
        "reasoning_80gb",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  developer:",
            "    port: 8081",
            "  tts:",
            "    port: 9001",
        ],
        bootstrap_content="#!/usr/bin/env bash\nset -e\necho reasoning\n",
        config_yaml_lines=["combo_tag: reasoning_80gb"],
    )

    base = {"provider": "vast"}
    cli = {}

    state_a = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a,
    )

    expected_manifest_a = yaml.safe_load((deepseek_dir / "combo.yaml").read_text(encoding="utf-8"))
    expected_manifest_b = yaml.safe_load((reasoning_dir / "combo.yaml").read_text(encoding="utf-8"))

    assert state_a["combo_manifest"] == expected_manifest_a
    assert state_b["combo_manifest"] == expected_manifest_b
    assert state_a["combo_manifest"] is not state_b["combo_manifest"]
    assert "stt" in state_a["combo_manifest"]["services"]
    assert "stt" not in state_b["combo_manifest"]["services"]

    state_a_repeat = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b_repeat = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a_repeat,
    )

    manifest_b_canonical = json.dumps(state_b["combo_manifest"], sort_keys=True, separators=(",", ":"))
    manifest_b_repeat_canonical = json.dumps(
        state_b_repeat["combo_manifest"], sort_keys=True, separators=(",", ":")
    )
    assert manifest_b_repeat_canonical == manifest_b_canonical


def test_combo_switch_reloads_bootstrap_script(tmp_path):
    module = _load_combo_manager_module()
    combos_root = tmp_path / "combos"

    deepseek_bootstrap = "#!/usr/bin/env bash\nset -e\necho deepseek\n"
    reasoning_bootstrap = "#!/usr/bin/env bash\nset -e\necho reasoning\n"

    deepseek_dir = _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
        ],
        bootstrap_content=deepseek_bootstrap,
        config_yaml_lines=["combo_tag: deepseek_whisper"],
    )
    reasoning_dir = _create_combo(
        combos_root,
        "reasoning_80gb",
        "reasoning_80gb",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  developer:",
            "    port: 8081",
        ],
        bootstrap_content=reasoning_bootstrap,
        config_yaml_lines=["combo_tag: reasoning_80gb"],
    )

    base = {"provider": "vast"}
    cli = {}

    state_a = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a,
    )

    expected_a = (deepseek_dir / "bootstrap.sh").read_text(encoding="utf-8")
    expected_b = (reasoning_dir / "bootstrap.sh").read_text(encoding="utf-8")

    assert state_a["bootstrap_script"] == expected_a
    assert state_b["bootstrap_script"] == expected_b
    assert state_b["bootstrap_script"] != state_a["bootstrap_script"]

    state_a_repeat = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b_repeat = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a_repeat,
    )
    assert state_b_repeat["bootstrap_script"].encode("utf-8") == state_b["bootstrap_script"].encode(
        "utf-8"
    )


def test_combo_switch_resets_runtime_configuration(tmp_path):
    module = _load_combo_manager_module()
    combos_root = tmp_path / "combos"

    _create_combo(
        combos_root,
        "deepseek_whisper",
        "deepseek_whisper",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  stt:",
            "    port: 9000",
        ],
        bootstrap_content="#!/usr/bin/env bash\nset -e\necho deepseek\n",
        config_yaml_lines=[
            "combo_tag: deepseek_whisper",
            "deepseek_only: true",
            "idle_timeout_seconds: 1800",
        ],
    )
    _create_combo(
        combos_root,
        "reasoning_80gb",
        "reasoning_80gb",
        services_yaml_lines=[
            "  architect:",
            "    port: 8080",
            "  developer:",
            "    port: 8081",
            "  tts:",
            "    port: 9001",
        ],
        bootstrap_content="#!/usr/bin/env bash\nset -e\necho reasoning\n",
        config_yaml_lines=[
            "combo_tag: reasoning_80gb",
            "reasoning_mode: strict",
            "idle_timeout_seconds: 1200",
        ],
    )

    base = {
        "provider": "vast",
        "region": "global",
        "idle_timeout_seconds": 9999,
    }
    cli = {"idle_timeout_seconds": 900, "allow_multiple": False}

    state_a = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a,
    )

    assert state_a["runtime_config"]["combo_tag"] == "deepseek_whisper"
    assert state_b["runtime_config"]["combo_tag"] == "reasoning_80gb"
    assert "deepseek_only" in state_a["runtime_config"]
    assert "deepseek_only" not in state_b["runtime_config"]
    assert state_b["runtime_config"]["reasoning_mode"] == "strict"
    assert state_b["runtime_config"]["idle_timeout_seconds"] == 900

    state_a["runtime_config"]["idle_timeout_seconds"] = 111
    assert state_b["runtime_config"]["idle_timeout_seconds"] == 900

    state_a_repeat = _resolve_state(module, combos_root, "deepseek_whisper", base, cli)
    state_b_repeat = _resolve_state(
        module,
        combos_root,
        "reasoning_80gb",
        base,
        cli,
        previous_runtime_state=state_a_repeat,
    )
    assert _canonical_runtime_projection(state_b_repeat) == _canonical_runtime_projection(state_b)
