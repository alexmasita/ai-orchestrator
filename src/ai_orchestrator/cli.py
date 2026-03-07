from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ai_orchestrator.config import ConfigError, load_config
from ai_orchestrator.core.combo_manager import resolve_runtime_state_for_combo
from ai_orchestrator.orchestrator import (
    OfferSelectionError,
    build_vast_search_requirements,
    resolve_combo_endpoints,
    run_orchestration,
    select_offer,
)
from ai_orchestrator.provider.vast import VastProvider, VastProviderError
from ai_orchestrator.runtime.script import render_bootstrap_script
from ai_orchestrator.sizing import OrchestratorConfigError, SizingInput, compute_requirements


def format_json_output(payload):
    return json.dumps(payload, sort_keys=True)


def format_list_output(instances):
    ordered_instances = sorted(
        [dict(instance) for instance in instances],
        key=lambda item: str(item.get("instance_id", "")),
    )
    return json.dumps({"instances": ordered_instances}, sort_keys=True)


class _CLIArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args=args, namespace=namespace)
        if getattr(parsed, "command", None) != "start":
            return parsed

        has_combo = getattr(parsed, "combo", None) is not None
        if has_combo:
            if getattr(parsed, "config", None) in (None, ""):
                parsed.config = "config.yaml"
            return parsed

        has_models = bool(getattr(parsed, "models", None))
        if has_models and getattr(parsed, "config", None) in (None, ""):
            self.error("the following arguments are required: --config")
        return parsed


def build_parser():
    parser = _CLIArgumentParser(prog="ai-orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--config")
    mode_group = start_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--models", nargs="+")
    mode_group.add_argument("--combo")
    start_parser.add_argument("--allow-multiple", action="store_true")
    subparsers.add_parser("docs")

    return parser


def _maybe_load_combo_base_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}
    try:
        return load_config(config_path)
    except ConfigError:
        # In combo mode config is optional; missing default config is not fatal.
        if config_path == "config.yaml" and not Path(config_path).exists():
            return {}
        raise


def _has_active_instances(instances: Any) -> bool:
    active_statuses = {"running", "loading", "starting"}
    if not isinstance(instances, list):
        instances = [instances]

    for instance in instances:
        status: Any = None
        if isinstance(instance, dict):
            status = (
                instance.get("status")
                or instance.get("actual_status")
                or instance.get("state")
            )
        else:
            status = (
                getattr(instance, "status", None)
                or getattr(instance, "actual_status", None)
                or getattr(instance, "state", None)
            )
        if isinstance(status, str) and status.lower() in active_statuses:
            return True
    return False


def _build_combo_bootstrap_env(runtime_state: dict[str, Any]) -> dict[str, str]:
    runtime_config = runtime_state.get("runtime_config", {})
    ports = runtime_state.get("ports", {})
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    if not isinstance(ports, dict):
        ports = {}

    env: dict[str, str] = {}

    def _maybe_set(name: str, value: Any) -> None:
        if value is None:
            return
        env[name] = str(value)

    _maybe_set("AI_ORCH_ARCHITECT_PORT", ports.get("architect"))
    _maybe_set("AI_ORCH_DEVELOPER_PORT", ports.get("developer"))
    _maybe_set("AI_ORCH_STT_PORT", ports.get("stt"))
    _maybe_set("AI_ORCH_TTS_PORT", ports.get("tts"))
    _maybe_set("AI_ORCH_CONTROL_PORT", ports.get("control"))
    _maybe_set("AI_ORCH_IDLE_TIMEOUT", runtime_config.get("idle_timeout_seconds"))

    return {key: env[key] for key in sorted(env.keys())}


def _instance_to_payload(instance: Any) -> dict[str, Any]:
    if isinstance(instance, dict):
        return dict(instance)

    payload: dict[str, Any] = {}
    for attr in (
        "instance_id",
        "gpu_name",
        "gpu_type",
        "dph",
        "cost_per_hour",
        "actual_status",
        "public_ipaddr",
        "public_ip",
        "ports",
    ):
        if hasattr(instance, attr):
            payload[attr] = getattr(instance, attr)
    if "public_ipaddr" not in payload and "public_ip" not in payload and hasattr(instance, "public_ip"):
        payload["public_ipaddr"] = getattr(instance, "public_ip")
    return payload


def run_combo_start(args) -> int:
    try:
        base_config = _maybe_load_combo_base_config(args.config)
        runtime_state = resolve_runtime_state_for_combo(
            combos_root="combos",
            combo_name=args.combo,
            base_config=base_config,
            cli_overrides={},
        )
        runtime_config = runtime_state.get("runtime_config", {})
        if not isinstance(runtime_config, dict):
            runtime_config = {}

        provider = VastProvider(
            api_key=str(runtime_config.get("vast_api_key", "")),
            base_url=str(
                runtime_config.get("vast_api_url", "https://console.vast.ai/api/v0")
            ),
        )

        existing_instances = provider.list_instances()
        if _has_active_instances(existing_instances) and not bool(args.allow_multiple):
            print(
                "Start blocked: existing instance detected. Use --allow-multiple to continue.",
                file=sys.stderr,
            )
            return 1

        raw_bootstrap_script = str(runtime_state.get("bootstrap_script", ""))
        rendered_bootstrap_script = render_bootstrap_script(
            raw_bootstrap_script,
            _build_combo_bootstrap_env(runtime_state),
        )

        instance_config: dict[str, Any] = {
            "bootstrap_script": rendered_bootstrap_script,
            "ports": runtime_state.get("ports", {}),
            "combo_name": str(runtime_state.get("combo_name") or args.combo),
        }
        if isinstance(runtime_config.get("bootstrap_base_url"), str) and runtime_config.get(
            "bootstrap_base_url"
        ):
            instance_config["bootstrap_base_url"] = str(runtime_config["bootstrap_base_url"])
        instance_config["runtime_config"] = {"bootstrap_base_url": runtime_config.get("bootstrap_base_url")}
        if runtime_config.get("min_disk_gb") is not None:
            instance_config["disk"] = runtime_config["min_disk_gb"]
        if runtime_config.get("idle_timeout_seconds") is not None:
            instance_config["env"] = {
                "IDLE_TIMEOUT_SECONDS": str(runtime_config["idle_timeout_seconds"])
            }

        search_requirements = build_vast_search_requirements(runtime_config)
        selected_offer = select_offer(
            provider,
            config=runtime_config,
            required_vram_gb=search_requirements["required_vram_gb"],
            search_requirements=search_requirements,
        )
        offer_id = str(getattr(selected_offer, "id", ""))
        if offer_id == "":
            raise ValueError("No qualifying offers found")

        snapshot_version = str(runtime_config.get("snapshot_version", ""))
        created_instance = provider.create_instance(
            offer_id,
            snapshot_version,
            instance_config,
        )
        created_payload = _instance_to_payload(created_instance)
        instance_id = created_payload.get("instance_id")
        if instance_id in (None, ""):
            raise ValueError("Provider create_instance response missing instance_id")

        polled_payload: dict[str, Any] = created_payload
        poll_fn = getattr(provider, "poll_instance", None)
        if callable(poll_fn):
            latest = poll_fn(str(instance_id))
            if isinstance(latest, dict):
                polled_payload = dict(latest)
            else:
                polled_payload = _instance_to_payload(latest)

        endpoints = resolve_combo_endpoints(
            polled_payload,
            runtime_state.get("combo_manifest", runtime_state),
        )

        result = {
            "instance_id": polled_payload.get("instance_id", created_payload.get("instance_id")),
            "gpu_type": polled_payload.get("gpu_type")
            or polled_payload.get("gpu_name")
            or created_payload.get("gpu_type")
            or created_payload.get("gpu_name"),
            "cost_per_hour": polled_payload.get("cost_per_hour")
            or polled_payload.get("dph")
            or created_payload.get("cost_per_hour")
            or created_payload.get("dph"),
            "architect_url": endpoints.get("architect_url"),
            "developer_url": endpoints.get("developer_url"),
            "stt_url": endpoints.get("stt_url"),
            "tts_url": endpoints.get("tts_url"),
            "control_url": endpoints.get("control_url"),
            "snapshot_version": snapshot_version,
            "idle_timeout": runtime_config.get("idle_timeout_seconds"),
        }
        print(format_json_output(result), end="")
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except VastProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, OfferSelectionError) as exc:
        print(f"Combo start error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Combo start error: {exc}", file=sys.stderr)
        return 1


def run_legacy_start(args) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    sizing_input = SizingInput(models=args.models, config=config)
    try:
        sizing_result = compute_requirements(sizing_input)
        provider = VastProvider(api_key=config["vast_api_key"], base_url=config["vast_api_url"])
        raw_result = run_orchestration(
            provider=provider,
            sizing_result=sizing_result,
            config=config,
        )
    except OrchestratorConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except VastProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1
    gpu_type = raw_result.get("gpu_type") or raw_result.get("gpu_name")
    cost_per_hour = raw_result.get("cost_per_hour") or raw_result.get("dph")
    result = {
        "instance_id": raw_result["instance_id"],
        "gpu_type": gpu_type,
        "cost_per_hour": cost_per_hour,
        "idle_timeout": raw_result["idle_timeout"],
        "snapshot_version": raw_result["snapshot_version"],
        "deepseek_url": raw_result.get("deepseek_url", "http://127.0.0.1:8080"),
        "whisper_url": raw_result.get("whisper_url", "http://127.0.0.1:9000"),
    }
    print(format_json_output(result), end="")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "docs":
        try:
            from ai_orchestrator.devserver.app import run_dev_server
        except ModuleNotFoundError as exc:
            if exc.name in {"fastapi", "uvicorn"}:
                print(
                    "Missing optional dependencies for docs server. "
                    "Install with: pip install -e .[devdocs]",
                    file=sys.stderr,
                )
                return 1
            raise
        run_dev_server()
        return 0

    if args.command != "start":
        return 1

    if getattr(args, "combo", None):
        return run_combo_start(args)

    return run_legacy_start(args)
