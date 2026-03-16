from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from ai_orchestrator.combos.loader import load_combo
from ai_orchestrator.config_merge import merge_config_layers
from ai_orchestrator.core.service_registry import ServiceRegistry
from ai_orchestrator.core.snapshot_manager import compute_snapshot_namespace

_RUNTIME_INFRA_KEYS = {
    "allow_interruptible",
    "gpu",
    "image",
    "idle_timeout_seconds",
    "instance_ready_timeout_seconds",
    "limit",
    "max_dph",
    "min_disk_gb",
    "min_inet_down_mbps",
    "min_inet_up_mbps",
    "min_reliability",
    "runtime_file_paths",
    "snapshot_version",
    "vast_api_key",
    "vast_api_url",
    "verified_only",
    "whisper_disk_gb",
    "whisper_vram_gb",
}


def _load_runtime_config_asset(combo_name: str) -> dict[str, Any]:
    config_path = Path.cwd() / "configs" / f"{combo_name}.yaml"
    if not config_path.is_file():
        return {}

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid YAML object in {config_path}")
    return dict(payload)


def resolve_runtime_config_for_combo(
    combos_root: str | Path,
    combo_name: str,
    base_config: dict[str, Any] | None,
    cli_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    combo = load_combo(combos_root, combo_name)
    runtime_asset_config = _load_runtime_config_asset(combo.name)
    cli = dict(cli_overrides or {})

    merged = merge_config_layers(base_config or {}, runtime_asset_config, combo.combo_config)
    resolved = merge_config_layers(merged, {}, cli)

    # When configs/<combo>.yaml exists, its infrastructure keys remain authoritative
    # unless explicitly overridden by CLI.
    if runtime_asset_config:
        for key in sorted(_RUNTIME_INFRA_KEYS):
            if key in runtime_asset_config and key not in cli:
                resolved[key] = deepcopy(runtime_asset_config[key])
        # Treat this as a combo-local marker that should not leak into runtime infra config.
        resolved.pop("combo_runtime_source", None)

    return resolved


def _derive_ports_from_manifest(manifest: dict[str, Any]) -> dict[str, int]:
    raw_services = manifest.get("services", {})
    if not isinstance(raw_services, dict):
        return {}

    ports: dict[str, int] = {}
    for service_name in sorted(raw_services.keys()):
        service_payload = raw_services.get(service_name, {})
        if not isinstance(service_payload, dict):
            continue
        raw_port = service_payload.get("port")
        if isinstance(raw_port, bool):
            continue
        try:
            ports[service_name] = int(raw_port)
        except (TypeError, ValueError):
            continue
    return ports


def resolve_runtime_state_for_combo(
    combos_root: str | Path,
    combo_name: str,
    base_config: dict[str, Any] | None,
    cli_overrides: dict[str, Any] | None,
    previous_runtime_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = previous_runtime_state
    combo = load_combo(combos_root, combo_name)
    runtime_config = resolve_runtime_config_for_combo(
        combos_root=combos_root,
        combo_name=combo_name,
        base_config=base_config or {},
        cli_overrides=cli_overrides or {},
    )
    service_registry = ServiceRegistry.from_combo_manifest(combo.combo_manifest)
    ports = _derive_ports_from_manifest(combo.combo_manifest)

    raw_snapshot_version = runtime_config.get("snapshot_version", "")
    snapshot_version = str(raw_snapshot_version)
    snapshot_namespace = compute_snapshot_namespace(
        combo_name=combo.name,
        snapshot_version=snapshot_version,
    )

    return {
        "combo_name": combo.name,
        "combo_manifest": deepcopy(combo.combo_manifest),
        "bootstrap_script": str(combo.bootstrap_script),
        "runtime_config": runtime_config,
        "service_registry": service_registry,
        "ports": ports,
        "snapshot_namespace": snapshot_namespace,
    }
