from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from ai_orchestrator.combos.loader import discover_combos
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

DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_COMBOS_ROOT = "combos"
DEFAULT_RUNTIME_RECORD_DIR = ".ai-orchestrator/runtime"
_TRANSITIONAL_INSTANCE_STATES = {"connecting", "creating", "loading", "scheduling", "starting"}
_STARTABLE_INSTANCE_STATES = {"exited", "inactive", "stopped"}
_UNAVAILABLE_INSTANCE_STATES = {"offline"}
_NEUROFLOW_RUNTIME_SCHEMA_VERSION = "2026-03-15-neuroflow-runtime-v1"
_NEUROFLOW_RUNTIME_PROBES_SCHEMA_VERSION = "2026-03-15-neuroflow-runtime-probes-v1"
_NEUROFLOW_PROBE_TIMEOUT_MS = 5000
_NEUROFLOW_STT_FIXTURE_PATH = Path("combos/neuroflow/assets/stt-probe.wav")


class _WizardCancelled(Exception):
    pass


class _WizardBack(Exception):
    pass


class _RestartTransitionTimeout(ValueError):
    def __init__(
        self,
        instance_id: str,
        status: str,
        timeout_seconds: float,
        payload: dict[str, Any] | None = None,
    ):
        self.instance_id = str(instance_id)
        self.status = str(status)
        self.timeout_seconds = float(timeout_seconds)
        self.payload = dict(payload or {})
        timeout_label = (
            str(int(self.timeout_seconds))
            if float(self.timeout_seconds).is_integer()
            else str(self.timeout_seconds)
        )
        super().__init__(
            f"Instance {self.instance_id} remained in {self.status} beyond "
            f"restart_transition_timeout_seconds={timeout_label}; "
            "start a new instance or destroy the stuck one."
        )


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
        command = getattr(parsed, "command", None)
        if command == "start":
            has_combo = getattr(parsed, "combo", None) is not None
            if has_combo and getattr(parsed, "config", None) in (None, ""):
                parsed.config = DEFAULT_CONFIG_PATH
                return parsed

            has_models = bool(getattr(parsed, "models", None))
            if has_models and getattr(parsed, "config", None) in (None, ""):
                self.error("the following arguments are required: --config")
            return parsed

        if command in {"resolve", "wizard"} and getattr(parsed, "config", None) in (None, ""):
            parsed.config = DEFAULT_CONFIG_PATH
        return parsed


def build_parser():
    parser = _CLIArgumentParser(
        prog="ai-orchestrator",
        description="Launch, resolve, and publish combo runtimes on Vast.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  ai-orchestrator wizard\n"
            "  ai-orchestrator wizard --combo neuroflow\n"
            "  ai-orchestrator wizard --config alt-config.yaml\n"
            "  ai-orchestrator wizard  # defaults runtime output to .ai-orchestrator/runtime/<combo>-runtime.json when none is configured\n"
            "  ai-orchestrator combos\n"
            "  ai-orchestrator start --combo neuroflow\n"
            "  ai-orchestrator resolve --combo neuroflow --instance-id 32890211\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start a runtime")
    start_parser.add_argument("--config", help="Config path. Optional for combo mode.")
    mode_group = start_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--models", nargs="+")
    mode_group.add_argument("--combo")
    start_parser.add_argument("--allow-multiple", action="store_true")
    start_parser.add_argument(
        "--write-runtime-file",
        action="append",
        dest="runtime_file_paths",
        default=[],
        help="Additional runtime record file path. May be passed multiple times.",
    )

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve a combo instance into live endpoints and publish a runtime record.",
    )
    resolve_parser.add_argument("--combo", required=True)
    resolve_parser.add_argument("--instance-id", required=True)
    resolve_parser.add_argument("--config", help="Optional config path. Defaults to config.yaml.")
    resolve_parser.add_argument(
        "--write-runtime-file",
        action="append",
        dest="runtime_file_paths",
        default=[],
        help="Additional runtime record file path. May be passed multiple times.",
    )

    wizard_parser = subparsers.add_parser(
        "wizard",
        help="Interactive guided workflow for combo selection, runtime resolution, and publication.",
    )
    wizard_parser.add_argument("--combo", help="Optional combo name to skip combo selection.")
    wizard_parser.add_argument("--config", help="Optional config path. Defaults to config.yaml.")
    wizard_parser.add_argument(
        "--write-runtime-file",
        action="append",
        dest="runtime_file_paths",
        default=[],
        help="Additional runtime record file path. May be passed multiple times.",
    )

    subparsers.add_parser("combos", help="List available combos discovered from the repo.")
    subparsers.add_parser("docs")

    return parser


def _maybe_load_combo_base_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}
    try:
        return load_config(config_path)
    except ConfigError:
        if config_path == DEFAULT_CONFIG_PATH and not Path(config_path).exists():
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

    for service_name in sorted(ports.keys()):
        normalized_service = re.sub(r"[^A-Za-z0-9]+", "_", str(service_name)).strip("_").upper()
        if normalized_service == "":
            continue
        _maybe_set(f"AI_ORCH_{normalized_service}_PORT", ports.get(service_name))

    idle_timeout_seconds = runtime_config.get("idle_timeout_seconds")
    _maybe_set("AI_ORCH_IDLE_TIMEOUT", idle_timeout_seconds)
    _maybe_set("AI_ORCH_IDLE_TIMEOUT_SECONDS", idle_timeout_seconds)

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
        "status",
        "public_ipaddr",
        "public_ip",
        "ports",
        "label",
    ):
        if hasattr(instance, attr):
            payload[attr] = getattr(instance, attr)
    if "public_ipaddr" not in payload and "public_ip" not in payload and hasattr(instance, "public_ip"):
        payload["public_ipaddr"] = getattr(instance, "public_ip")
    return payload


def _discover_combo_names(combos_root: str | Path = DEFAULT_COMBOS_ROOT) -> list[str]:
    return discover_combos(combos_root)


def _normalize_instance_status(payload: dict[str, Any]) -> str:
    raw_status = payload.get("status", payload.get("actual_status", payload.get("state", "unknown")))
    if not isinstance(raw_status, str):
        return "unknown"
    normalized = raw_status.strip().lower()
    return normalized if normalized else "unknown"


def _status_sort_key(status: str) -> tuple[int, str]:
    if status == "running":
        return (0, status)
    if status in _STARTABLE_INSTANCE_STATES:
        return (1, status)
    if status in _TRANSITIONAL_INSTANCE_STATES:
        return (2, status)
    if status in _UNAVAILABLE_INSTANCE_STATES:
        return (3, status)
    return (4, status)


def _resolve_combo_readiness_timeout_seconds(runtime_config: dict[str, Any]) -> float:
    raw_timeout = runtime_config.get("instance_ready_timeout_seconds", 180)
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError):
        timeout_seconds = 180.0
    if timeout_seconds <= 0:
        timeout_seconds = 180.0
    return timeout_seconds


def _resolve_restart_transition_timeout_seconds(runtime_config: dict[str, Any]) -> float:
    raw_timeout = runtime_config.get("restart_transition_timeout_seconds", 300)
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError):
        timeout_seconds = 300.0
    if timeout_seconds <= 0:
        timeout_seconds = 300.0
    return timeout_seconds


def _poll_combo_endpoints_until_mapped(
    provider: Any,
    instance_id: str,
    combo_manifest: dict[str, Any],
    initial_payload: dict[str, Any],
    *,
    timeout_seconds: float,
    poll_interval_seconds: float = 2.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    latest_payload = dict(initial_payload)
    latest_endpoints = resolve_combo_endpoints(latest_payload, combo_manifest)

    services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}
    expected_endpoint_count = len(services) if isinstance(services, dict) else 0
    if expected_endpoint_count == 0 or len(latest_endpoints) >= expected_endpoint_count:
        return latest_payload, latest_endpoints

    poll_fn = getattr(provider, "poll_instance", None)
    if not callable(poll_fn):
        return latest_payload, latest_endpoints

    deadline = time.monotonic() + float(timeout_seconds)
    while time.monotonic() < deadline:
        time.sleep(float(poll_interval_seconds))
        polled = poll_fn(str(instance_id))
        latest_payload = dict(polled) if isinstance(polled, dict) else _instance_to_payload(polled)
        latest_endpoints = resolve_combo_endpoints(latest_payload, combo_manifest)
        if len(latest_endpoints) >= expected_endpoint_count:
            break

    return latest_payload, latest_endpoints


def _fetch_combo_control_health(
    control_url: str,
    combo_manifest: dict[str, Any],
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, Any] | None:
    services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}
    control_payload = services.get("control", {}) if isinstance(services, dict) else {}
    health_path = "/health"
    if isinstance(control_payload, dict):
        raw_health_path = control_payload.get("health_path", "/health")
        if isinstance(raw_health_path, str) and raw_health_path.strip() != "":
            health_path = raw_health_path

    target_url = urljoin(control_url.rstrip("/") + "/", health_path.lstrip("/"))
    try:
        with urlopen(target_url, timeout=float(timeout_seconds)) as response:
            if getattr(response, "status", 200) != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _control_health_ready(health_payload: dict[str, Any], combo_manifest: dict[str, Any]) -> bool:
    if not isinstance(health_payload, dict):
        return False
    services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}
    health_services = health_payload.get("services", {})
    if not isinstance(services, dict) or not isinstance(health_services, dict):
        return False

    for service_name in sorted(services.keys()):
        service_result = health_services.get(service_name, {})
        if not isinstance(service_result, dict):
            return False
        if str(service_result.get("status", "")).lower() != "up":
            return False
    return True


def _services_not_ready(
    health_payload: dict[str, Any],
    combo_manifest: dict[str, Any],
) -> list[str]:
    services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}
    health_services = health_payload.get("services", {}) if isinstance(health_payload, dict) else {}
    if not isinstance(services, dict) or not isinstance(health_services, dict):
        return []

    unavailable: list[str] = []
    for service_name in sorted(services.keys()):
        service_result = health_services.get(service_name, {})
        if not isinstance(service_result, dict):
            unavailable.append(service_name)
            continue
        if str(service_result.get("status", "")).lower() != "up":
            unavailable.append(service_name)
    return unavailable


def _maybe_restart_instance_for_resolution(
    provider: Any,
    instance_id: str,
    payload: dict[str, Any],
    *,
    allow_restart: bool,
) -> None:
    status = _normalize_instance_status(payload)
    if status in _STARTABLE_INSTANCE_STATES:
        if not allow_restart:
            raise ValueError(f"Instance {instance_id} is {status}; restart not allowed in this flow")
        provider.set_instance_state(instance_id, "running")
    elif status in _UNAVAILABLE_INSTANCE_STATES:
        raise ValueError(f"Instance {instance_id} is {status}; create a new instance instead")


def _resolve_combo_runtime(
    provider: Any,
    instance_id: str,
    combo_manifest: dict[str, Any],
    runtime_config: dict[str, Any],
    *,
    initial_payload: dict[str, Any] | None = None,
    allow_restart: bool,
    restart_transition_extra_seconds: float = 0.0,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    poll_fn = getattr(provider, "poll_instance", None)
    if not callable(poll_fn):
        raise ValueError("Provider does not support poll_instance")

    latest_payload = dict(initial_payload or {})
    if not latest_payload:
        polled = poll_fn(str(instance_id))
        latest_payload = dict(polled) if isinstance(polled, dict) else _instance_to_payload(polled)

    last_progress_message: str | None = None

    def _report(message: str) -> None:
        nonlocal last_progress_message
        if status_callback is None or message == last_progress_message:
            return
        last_progress_message = message
        status_callback(message)

    initial_status = _normalize_instance_status(latest_payload)
    if initial_status in _STARTABLE_INSTANCE_STATES and allow_restart:
        _report(
            f"Restarting instance {instance_id} from {initial_status} state before resolving endpoints..."
        )

    _maybe_restart_instance_for_resolution(
        provider,
        str(instance_id),
        latest_payload,
        allow_restart=allow_restart,
    )

    timeout_seconds = _resolve_combo_readiness_timeout_seconds(runtime_config)
    restart_transition_timeout_seconds = (
        _resolve_restart_transition_timeout_seconds(runtime_config)
        + max(0.0, float(restart_transition_extra_seconds))
    )
    deadline = time.monotonic() + timeout_seconds
    last_stage = "instance"
    restart_transition_started_at: float | None = None
    restart_transition_deadline: float | None = None

    def _begin_restart_transition() -> None:
        nonlocal restart_transition_started_at, restart_transition_deadline
        if restart_transition_started_at is not None:
            return
        restart_transition_started_at = time.monotonic()
        restart_transition_deadline = restart_transition_started_at + restart_transition_timeout_seconds

    def _report_restart_wait(status: str) -> None:
        if restart_transition_started_at is None:
            return
        elapsed = max(0.0, time.monotonic() - restart_transition_started_at)
        elapsed_label = str(int(elapsed))
        timeout_label = (
            str(int(restart_transition_timeout_seconds))
            if float(restart_transition_timeout_seconds).is_integer()
            else str(restart_transition_timeout_seconds)
        )
        _report(
            f"Waiting for restarted instance {instance_id} to become runnable "
            f"(current: {status}, elapsed: {elapsed_label}s/{timeout_label}s)..."
        )

    def _maybe_raise_restart_timeout(status: str, payload: dict[str, Any]) -> None:
        if restart_transition_deadline is None:
            return
        if time.monotonic() < restart_transition_deadline:
            return
        raise _RestartTransitionTimeout(
            str(instance_id),
            status,
            restart_transition_timeout_seconds,
            payload=payload,
        )

    if initial_status in _STARTABLE_INSTANCE_STATES and allow_restart:
        _begin_restart_transition()

    while time.monotonic() < deadline:
        polled = poll_fn(str(instance_id))
        latest_payload = dict(polled) if isinstance(polled, dict) else _instance_to_payload(polled)
        status = _normalize_instance_status(latest_payload)
        if status in _STARTABLE_INSTANCE_STATES and allow_restart:
            if restart_transition_started_at is None:
                _begin_restart_transition()
                _report(f"Instance {instance_id} is {status}; requesting restart...")
                provider.set_instance_state(str(instance_id), "running")
            else:
                _report_restart_wait(status)
                _maybe_raise_restart_timeout(status, latest_payload)
            last_stage = "instance_restart"
            time.sleep(2.0)
            continue
        if status in _UNAVAILABLE_INSTANCE_STATES:
            raise ValueError(f"Instance {instance_id} became {status}; create a new instance instead")
        if status != "running" and status not in _TRANSITIONAL_INSTANCE_STATES:
            last_stage = f"instance_status:{status}"
            if restart_transition_started_at is not None:
                _report_restart_wait(status)
                _maybe_raise_restart_timeout(status, latest_payload)
            else:
                _report(f"Waiting for instance {instance_id} to become running (current: {status})...")
            time.sleep(2.0)
            continue
        if status in _TRANSITIONAL_INSTANCE_STATES:
            if restart_transition_started_at is not None:
                _report_restart_wait(status)
                _maybe_raise_restart_timeout(status, latest_payload)
            else:
                _report(
                    f"Waiting for instance {instance_id} to finish transitioning (current: {status})..."
                )
            time.sleep(2.0)
            continue

        last_stage = "ports"
        latest_payload, endpoints = _poll_combo_endpoints_until_mapped(
            provider,
            str(instance_id),
            combo_manifest,
            latest_payload,
            timeout_seconds=min(10.0, max(2.0, deadline - time.monotonic())),
        )
        services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}
        expected_endpoint_count = len(services) if isinstance(services, dict) else 0
        if expected_endpoint_count > 0 and len(endpoints) < expected_endpoint_count:
            _report(
                f"Waiting for public port mappings for instance {instance_id} "
                f"({len(endpoints)}/{expected_endpoint_count} resolved)..."
            )
            time.sleep(2.0)
            continue

        control_url = endpoints.get("control_url")
        if not control_url:
            _report(f"Waiting for control endpoint mapping for instance {instance_id}...")
            return latest_payload, endpoints, {}

        last_stage = "control_health"
        _report(f"Checking control health at {control_url}/health ...")
        health_payload = _fetch_combo_control_health(control_url, combo_manifest)
        if health_payload is None:
            _report(f"Waiting for control health endpoint at {control_url}/health ...")
            time.sleep(2.0)
            continue
        if not _control_health_ready(health_payload, combo_manifest):
            last_stage = "service_health"
            unavailable = _services_not_ready(health_payload, combo_manifest)
            if unavailable:
                _report(
                    "Waiting for services to report healthy: "
                    + ", ".join(unavailable)
                )
            time.sleep(2.0)
            continue
        _report(f"Instance {instance_id} is ready and all services are healthy.")
        return latest_payload, endpoints, health_payload

    raise ValueError(
        "Timed out waiting for combo runtime readiness "
        f"for instance {instance_id}; last_stage={last_stage}"
    )


def _timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _combo_runtime_filename(combo_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(combo_name).strip()).strip("-")
    if normalized == "":
        normalized = "runtime"
    return f"{normalized}-runtime.json"


def _default_runtime_file_path(combo_name: str) -> Path:
    return (Path.cwd() / DEFAULT_RUNTIME_RECORD_DIR / _combo_runtime_filename(combo_name)).resolve(
        strict=False
    )


def _looks_like_directory_path(raw_value: str, path: Path) -> bool:
    normalized = raw_value.strip()
    return normalized.endswith(("/", "\\")) or path.is_dir()


def _normalize_runtime_output_path(raw_value: Any, combo_name: str) -> Path | None:
    if not isinstance(raw_value, str):
        return None
    stripped = raw_value.strip()
    if stripped == "":
        return None
    path = Path(stripped).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if _looks_like_directory_path(stripped, path):
        path = path / _combo_runtime_filename(combo_name)
    return path.resolve(strict=False)


def _resolve_runtime_file_paths(
    runtime_config: dict[str, Any],
    extra_paths: list[str] | None,
    combo_name: str,
    *,
    include_default: bool = False,
) -> list[Path]:
    ordered_paths: list[Path] = []
    seen: set[str] = set()

    def _append_path(raw_value: Any) -> None:
        path = _normalize_runtime_output_path(raw_value, combo_name)
        if path is None:
            return
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        ordered_paths.append(path)

    runtime_paths = runtime_config.get("runtime_file_paths", [])
    if isinstance(runtime_paths, str):
        _append_path(runtime_paths)
    elif isinstance(runtime_paths, list):
        for item in runtime_paths:
            _append_path(item)

    for item in extra_paths or []:
        _append_path(item)

    if len(ordered_paths) == 0 and include_default:
        _append_path(str(_default_runtime_file_path(combo_name)))

    return ordered_paths


def _neuroflow_probe_file_path(runtime_path: Path) -> Path:
    return runtime_path.with_name(f"{runtime_path.stem}-probes{runtime_path.suffix or '.json'}")


def _neuroflow_capability_defaults() -> dict[str, dict[str, Any]]:
    return {
        "interpret": {
            "provider_kind": "vllm_openai_compatible",
            "api_style": "openai_chat_completions",
            "model_alias": "interpret",
            "upstream_model": "Qwen/Qwen3-32B-AWQ",
            "recommended_timeout_ms": 20000,
            "request_content_type": "application/json",
            "response_content_type": "application/json",
            "response_kind": "json",
        },
        "reasoner": {
            "provider_kind": "vllm_openai_compatible",
            "api_style": "openai_chat_completions",
            "model_alias": "reasoner",
            "upstream_model": "openai/gpt-oss-20b",
            "recommended_timeout_ms": 30000,
            "request_content_type": "application/json",
            "response_content_type": "application/json",
            "response_kind": "json",
        },
        "rerank": {
            "provider_kind": "vllm_openai_compatible",
            "api_style": "openai_rerank",
            "model_alias": "rerank",
            "upstream_model": "BAAI/bge-reranker-v2-m3",
            "recommended_timeout_ms": 15000,
            "request_content_type": "application/json",
            "response_content_type": "application/json",
            "response_kind": "json",
        },
        "stt": {
            "provider_kind": "faster_whisper_custom",
            "api_style": "openai_audio_transcriptions",
            "model_alias": "whisper-large-v3-turbo",
            "upstream_model": "openai/whisper-large-v3-turbo",
            "recommended_timeout_ms": 30000,
            "request_content_type": "multipart/form-data",
            "response_content_type": "application/json",
            "response_kind": "json",
        },
        "tts": {
            "provider_kind": "kokoro_fastapi_openai_compatible",
            "api_style": "openai_audio_speech",
            "model_alias": "kokoro",
            "upstream_model": "hexgrad/Kokoro-82M",
            "recommended_timeout_ms": 20000,
            "request_content_type": "application/json",
            "response_content_type": "audio/mpeg",
            "response_kind": "binary",
        },
        "control": {
            "provider_kind": "control_api",
            "api_style": "custom_health",
            "model_alias": None,
            "upstream_model": None,
            "recommended_timeout_ms": 5000,
            "request_content_type": "application/json",
            "response_content_type": "application/json",
            "response_kind": "json",
        },
    }


def _http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout_ms: int = _NEUROFLOW_PROBE_TIMEOUT_MS,
) -> dict[str, Any]:
    request = Request(url, data=body, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)

    started_at = time.monotonic()
    try:
        with urlopen(request, timeout=float(timeout_ms) / 1000.0) as response:
            payload = response.read()
            return {
                "ok": True,
                "http_status": int(getattr(response, "status", 200)),
                "headers": dict(response.headers.items()),
                "body": payload,
                "error": None,
                "duration_ms": int((time.monotonic() - started_at) * 1000),
            }
    except HTTPError as exc:
        try:
            payload = exc.read()
        except Exception:
            payload = b""
        return {
            "ok": False,
            "http_status": int(exc.code),
            "headers": dict(exc.headers.items()) if exc.headers is not None else {},
            "body": payload,
            "error": str(exc),
            "duration_ms": int((time.monotonic() - started_at) * 1000),
        }
    except (URLError, TimeoutError, ValueError) as exc:
        return {
            "ok": False,
            "http_status": None,
            "headers": {},
            "body": b"",
            "error": str(exc),
            "duration_ms": int((time.monotonic() - started_at) * 1000),
        }


def _resolve_neuroflow_stt_fixture_path() -> Path | None:
    candidate = _NEUROFLOW_STT_FIXTURE_PATH
    return candidate if candidate.exists() and candidate.is_file() else None


def _build_generated_stt_fixture(tts_probe_audio: bytes) -> tuple[bytes | None, str | None]:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        return None, "ffmpeg is not available"

    input_path: Path | None = None
    output_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as input_handle:
            input_handle.write(tts_probe_audio)
            input_path = Path(input_handle.name)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_handle:
            output_path = Path(output_handle.name)

        completed = subprocess.run(
            [ffmpeg_path, "-y", "-loglevel", "error", "-i", str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            return None, stderr or "ffmpeg conversion failed"
        return output_path.read_bytes(), None
    except OSError as exc:
        return None, str(exc)
    finally:
        for temp_path in (input_path, output_path):
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass


def _http_json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_ms: int = _NEUROFLOW_PROBE_TIMEOUT_MS,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    response = _http_request(
        url,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else None,
        body=body,
        timeout_ms=timeout_ms,
    )
    parsed_json = None
    if response["body"]:
        try:
            parsed_json = json.loads(response["body"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed_json = None
    response["json"] = parsed_json
    return response


def _multipart_form_request(
    url: str,
    *,
    field_name: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    timeout_ms: int = _NEUROFLOW_PROBE_TIMEOUT_MS,
) -> dict[str, Any]:
    boundary = "----ai-orch-neuroflow-probe-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    response = _http_request(
        url,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        body=body,
        timeout_ms=timeout_ms,
    )
    parsed_json = None
    if response["body"]:
        try:
            parsed_json = json.loads(response["body"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed_json = None
    response["json"] = parsed_json
    return response


def _normalize_chat_probe_response(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    sample = {
        "id": payload.get("id"),
        "object": payload.get("object"),
        "model": payload.get("model"),
    }
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message", {}) if isinstance(first, dict) else {}
        sample["finish_reason"] = first.get("finish_reason")
        sample["message"] = {
            "role": message.get("role"),
            "content_preview": (message.get("content") or "")[:160] if isinstance(message, dict) else None,
            "reasoning_preview": (message.get("reasoning") or "")[:160] if isinstance(message, dict) else None,
        }
    if isinstance(payload.get("usage"), dict):
        sample["usage"] = payload.get("usage")
    return sample


def _normalize_rerank_probe_response(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    sample = {
        "id": payload.get("id"),
        "model": payload.get("model"),
        "usage": payload.get("usage"),
        "results": [],
    }
    results = payload.get("results")
    if isinstance(results, list):
        for item in results[:3]:
            if not isinstance(item, dict):
                continue
            document = item.get("document", {}) if isinstance(item.get("document"), dict) else {}
            sample["results"].append(
                {
                    "index": item.get("index"),
                    "text": document.get("text"),
                    "relevance_score": item.get("relevance_score"),
                }
            )
    return sample


def _normalize_tts_probe_response(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body", b"") or b""
    headers = response.get("headers", {})
    content_type = headers.get("Content-Type") or headers.get("content-type") or "application/octet-stream"
    return {
        "http_status": response.get("http_status"),
        "content_type": content_type,
        "content_length": len(body),
        "binary_preview_base64": base64.b64encode(body[:16]).decode("ascii") if body else None,
    }


def _capability_health_url(base_url: str | None, service_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(base_url, str) or base_url.strip() == "":
        return None
    raw_path = "/health"
    if isinstance(service_payload, dict):
        raw_path = str(service_payload.get("health_path", "/health") or "/health")
    return urljoin(base_url.rstrip("/") + "/", raw_path.lstrip("/"))


def _build_neuroflow_runtime_bundle(
    runtime_state: dict[str, Any],
    result: dict[str, Any],
    health_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    combo_manifest = runtime_state.get("combo_manifest", {})
    services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}
    defaults = _neuroflow_capability_defaults()
    probe_timestamp = _timestamp_now()
    probes: dict[str, Any] = {}
    successful_probe_count = 0
    readiness_notes: list[str] = []
    capabilities: dict[str, Any] = {}
    tts_probe_audio: bytes | None = None
    capability_timeouts = {
        name: int(payload.get("recommended_timeout_ms", _NEUROFLOW_PROBE_TIMEOUT_MS))
        for name, payload in defaults.items()
    }

    control_health_services = (
        health_payload.get("services", {})
        if isinstance(health_payload, dict) and isinstance(health_payload.get("services"), dict)
        else {}
    )

    ordered_capabilities = ("interpret", "reasoner", "rerank", "stt", "tts", "control")
    for capability_name in ordered_capabilities:
        base_url = result.get(f"{capability_name}_url")
        service_payload = services.get(capability_name, {}) if isinstance(services, dict) else {}
        defaults_payload = defaults.get(capability_name, {})
        control_status = control_health_services.get(capability_name, {})
        ready_from_control = (
            isinstance(control_status, dict) and str(control_status.get("status", "")).lower() == "up"
        )
        capability = {
            "name": capability_name,
            "base_url": base_url,
            "health_url": _capability_health_url(base_url, service_payload),
            "provider_kind": defaults_payload.get("provider_kind"),
            "api_style": defaults_payload.get("api_style"),
            "model_alias": defaults_payload.get("model_alias"),
            "upstream_model": defaults_payload.get("upstream_model"),
            "auth_required": False,
            "ready": bool(ready_from_control and isinstance(base_url, str) and base_url != ""),
            "last_probe": probe_timestamp,
            "health_status": control_status.get("status") if isinstance(control_status, dict) else None,
            "health_http_status": control_status.get("code") if isinstance(control_status, dict) else 200,
            "recommended_timeout_ms": defaults_payload.get("recommended_timeout_ms"),
            "request_content_type": defaults_payload.get("request_content_type"),
            "response_content_type": defaults_payload.get("response_content_type"),
            "response_kind": defaults_payload.get("response_kind"),
            "probe_error": None,
        }
        if capability_name == "stt":
            capability["probe_strategy"] = None
            capability["probe_latency_ms"] = None
        capabilities[capability_name] = capability

    if isinstance(result.get("control_url"), str):
        control_probe = _http_json_request(
            urljoin(result["control_url"].rstrip("/") + "/", "status"),
            timeout_ms=capability_timeouts.get("control", _NEUROFLOW_PROBE_TIMEOUT_MS),
        )
        probes["control"] = {
            "probe_request_description": "GET /status",
            "probe_http_status": control_probe.get("http_status"),
            "response_sample": control_probe.get("json"),
        }
        if control_probe.get("ok") and isinstance(control_probe.get("json"), dict):
            successful_probe_count += 1
        else:
            capabilities["control"]["probe_incomplete"] = True
            capabilities["control"]["probe_error"] = (
                control_probe.get("error") or "unexpected response"
            )
            readiness_notes.append(
                f"Control status probe incomplete: {control_probe.get('error') or 'unexpected response'}."
            )

    if isinstance(result.get("interpret_url"), str):
        interpret_request = {
            "model": "interpret",
            "messages": [{"role": "user", "content": "cheap sneakers near cinema"}],
            "max_tokens": 32,
        }
        interpret_probe = _http_json_request(
            urljoin(result["interpret_url"].rstrip("/") + "/", "v1/chat/completions"),
            method="POST",
            payload=interpret_request,
            timeout_ms=capability_timeouts.get("interpret", _NEUROFLOW_PROBE_TIMEOUT_MS),
        )
        probes["interpret"] = {
            "probe_request": interpret_request,
            "probe_http_status": interpret_probe.get("http_status"),
            "response_sample": _normalize_chat_probe_response(interpret_probe.get("json")),
        }
        if interpret_probe.get("ok") and isinstance(interpret_probe.get("json"), dict):
            successful_probe_count += 1
        else:
            capabilities["interpret"]["probe_incomplete"] = True
            capabilities["interpret"]["probe_error"] = (
                interpret_probe.get("error") or "unexpected response"
            )
            readiness_notes.append(
                f"Interpret probe incomplete: {interpret_probe.get('error') or 'unexpected response'}."
            )

    if isinstance(result.get("reasoner_url"), str):
        reasoner_request = {
            "model": "reasoner",
            "messages": [
                {"role": "user", "content": "Summarize the likely user goal in one sentence."}
            ],
            "max_tokens": 48,
        }
        reasoner_probe = _http_json_request(
            urljoin(result["reasoner_url"].rstrip("/") + "/", "v1/chat/completions"),
            method="POST",
            payload=reasoner_request,
            timeout_ms=capability_timeouts.get("reasoner", _NEUROFLOW_PROBE_TIMEOUT_MS),
        )
        probes["reasoner"] = {
            "probe_request": reasoner_request,
            "probe_http_status": reasoner_probe.get("http_status"),
            "response_sample": _normalize_chat_probe_response(reasoner_probe.get("json")),
        }
        if reasoner_probe.get("ok") and isinstance(reasoner_probe.get("json"), dict):
            successful_probe_count += 1
        else:
            capabilities["reasoner"]["probe_incomplete"] = True
            capabilities["reasoner"]["probe_error"] = (
                reasoner_probe.get("error") or "unexpected response"
            )
            readiness_notes.append(
                f"Reasoner probe incomplete: {reasoner_probe.get('error') or 'unexpected response'}."
            )

    if isinstance(result.get("rerank_url"), str):
        rerank_request = {
            "model": "rerank",
            "query": "cheap sneakers near cinema",
            "documents": [
                "Nike running sneakers under 80 dollars near the cinema",
                "Burger combo near the food court",
                "Adidas shoes on sale near central atrium",
            ],
        }
        rerank_probe = _http_json_request(
            urljoin(result["rerank_url"].rstrip("/") + "/", "rerank"),
            method="POST",
            payload=rerank_request,
            timeout_ms=capability_timeouts.get("rerank", _NEUROFLOW_PROBE_TIMEOUT_MS),
        )
        probes["rerank"] = {
            "probe_request": rerank_request,
            "probe_http_status": rerank_probe.get("http_status"),
            "response_sample": _normalize_rerank_probe_response(rerank_probe.get("json")),
        }
        if rerank_probe.get("ok") and isinstance(rerank_probe.get("json"), dict):
            successful_probe_count += 1
        else:
            capabilities["rerank"]["probe_incomplete"] = True
            capabilities["rerank"]["probe_error"] = (
                rerank_probe.get("error") or "unexpected response"
            )
            readiness_notes.append(
                f"Rerank probe incomplete: {rerank_probe.get('error') or 'unexpected response'}."
            )

    if isinstance(result.get("tts_url"), str):
        tts_request = {"model": "kokoro", "voice": "af_heart", "input": "Welcome to NeuroFlow"}
        tts_probe = _http_request(
            urljoin(result["tts_url"].rstrip("/") + "/", "v1/audio/speech"),
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps(tts_request).encode("utf-8"),
            timeout_ms=capability_timeouts.get("tts", _NEUROFLOW_PROBE_TIMEOUT_MS),
        )
        probes["tts"] = {
            "probe_request": tts_request,
            "probe_http_status": tts_probe.get("http_status"),
            "response_sample": _normalize_tts_probe_response(tts_probe),
        }
        if tts_probe.get("ok") and tts_probe.get("body"):
            successful_probe_count += 1
            tts_probe_audio = tts_probe.get("body")
            capabilities["tts"]["health_http_status"] = tts_probe.get("http_status")
        else:
            capabilities["tts"]["probe_incomplete"] = True
            capabilities["tts"]["probe_error"] = tts_probe.get("error") or "unexpected response"
            readiness_notes.append(
                f"TTS probe incomplete: {tts_probe.get('error') or 'unexpected response'}."
            )

    if isinstance(result.get("stt_url"), str):
        fixture_path = _resolve_neuroflow_stt_fixture_path()
        stt_probe_bytes: bytes | None = None
        stt_probe_strategy = "unverified"
        stt_request_description = "multipart audio transcription probe"
        stt_fixture_error: str | None = None

        if fixture_path is not None:
            try:
                stt_probe_bytes = fixture_path.read_bytes()
                stt_probe_strategy = "fixture"
                stt_request_description = "multipart audio transcription probe using deterministic WAV fixture"
            except OSError as exc:
                stt_fixture_error = str(exc)

        if stt_probe_bytes is None and tts_probe_audio:
            generated_bytes, generated_error = _build_generated_stt_fixture(tts_probe_audio)
            if generated_bytes is not None:
                stt_probe_bytes = generated_bytes
                stt_probe_strategy = "generated"
                stt_request_description = "multipart audio transcription probe using generated WAV fallback"
            else:
                stt_fixture_error = generated_error or stt_fixture_error

        if stt_probe_bytes is not None:
            stt_probe = _multipart_form_request(
                urljoin(result["stt_url"].rstrip("/") + "/", "v1/audio/transcriptions"),
                field_name="file",
                filename="stt-probe.wav",
                content_type="audio/wav",
                file_bytes=stt_probe_bytes,
                timeout_ms=capability_timeouts.get("stt", _NEUROFLOW_PROBE_TIMEOUT_MS),
            )
            probes["stt"] = {
                "probe_strategy": stt_probe_strategy,
                "probe_request_description": stt_request_description,
                "probe_http_status": stt_probe.get("http_status"),
                "probe_latency_ms": stt_probe.get("duration_ms"),
                "response_sample": stt_probe.get("json"),
            }
            capabilities["stt"]["probe_strategy"] = stt_probe_strategy
            capabilities["stt"]["probe_latency_ms"] = stt_probe.get("duration_ms")
            if stt_probe.get("ok") and isinstance(stt_probe.get("json"), dict):
                successful_probe_count += 1
                capabilities["stt"]["health_http_status"] = stt_probe.get("http_status")
            else:
                capabilities["stt"]["probe_incomplete"] = True
                capabilities["stt"]["probe_error"] = stt_probe.get("error") or "unexpected response"
                probes["stt"]["probe_error"] = stt_probe.get("error") or "unexpected response"
                diagnostic = f"HTTP {stt_probe['http_status']}" if stt_probe.get("http_status") else (
                    stt_probe.get("error") or "unexpected response"
                )
                readiness_notes.append(
                    f"STT probe incomplete via {stt_probe_strategy}: {diagnostic}."
                )
        else:
            capabilities["stt"]["probe_incomplete"] = True
            capabilities["stt"]["probe_strategy"] = "unverified"
            capabilities["stt"]["probe_error"] = (
                stt_fixture_error or "No STT probe fixture was available and no generated fallback could be built."
            )
            probes["stt"] = {
                "probe_strategy": "unverified",
                "probe_request_description": "multipart audio transcription probe",
                "probe_http_status": None,
                "probe_latency_ms": None,
                "probe_error": capabilities["stt"]["probe_error"],
                "response_sample": {"reason": capabilities["stt"]["probe_error"]},
            }
            readiness_notes.append(
                f"STT probe incomplete via unverified: {capabilities['stt']['probe_error']}."
            )

    for capability_name, capability in capabilities.items():
        if capability_name not in probes and capability_name != "control":
            capability["probe_incomplete"] = True

    live_integration_ready = True
    for capability_name in ("interpret", "reasoner", "rerank", "stt", "tts", "control"):
        capability = capabilities.get(capability_name, {})
        if not capability.get("ready", False):
            live_integration_ready = False
        if capability.get("probe_incomplete"):
            live_integration_ready = False

    enriched_result = dict(result)
    enriched_result["runtime_schema_version"] = _NEUROFLOW_RUNTIME_SCHEMA_VERSION
    enriched_result["runtime_readiness"] = {
        "live_integration_ready": live_integration_ready,
        "notes": readiness_notes,
    }
    enriched_result["capabilities"] = capabilities

    if successful_probe_count == 0:
        return enriched_result, None

    probe_payload = {
        "runtime_schema_version": _NEUROFLOW_RUNTIME_PROBES_SCHEMA_VERSION,
        "resolved_at": result.get("resolved_at"),
        "instance_id": result.get("instance_id"),
        "capability_probes": probes,
    }
    return enriched_result, probe_payload


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
    ) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _publication_status_for_entries(entries: list[dict[str, Any]]) -> str:
    if len(entries) == 0:
        return "not_requested"
    written_count = sum(1 for entry in entries if entry.get("status") == "written")
    if written_count == len(entries):
        return "success"
    if written_count == 0:
        return "failed"
    return "partial"


def _publish_runtime_record(
    base_payload: dict[str, Any],
    runtime_paths: list[Path],
    probe_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    entries: list[dict[str, Any]] = []
    for path in runtime_paths:
        entries.append(
            {"path": str(path), "status": "written", "error": None, "kind": "runtime"}
        )
        if probe_payload is not None:
            entries.append(
                {
                    "path": str(_neuroflow_probe_file_path(path)),
                    "status": "written",
                    "error": None,
                    "kind": "probe",
                }
            )
    if len(entries) == 0:
        payload = dict(base_payload)
        payload["publication_status"] = "not_requested"
        payload["runtime_file_writes"] = []
        return payload, 0

    payload = dict(base_payload)
    for _ in range(3):
        payload["publication_status"] = _publication_status_for_entries(entries)
        payload["runtime_file_writes"] = [
            {"path": entry["path"], "status": entry["status"], "error": entry["error"]}
            for entry in entries
        ]
        serialized = format_json_output(payload)
        probe_serialized = format_json_output(probe_payload) if probe_payload is not None else None
        changed = False
        for entry in entries:
            if entry["status"] != "written":
                continue
            try:
                content = serialized if entry["kind"] == "runtime" else str(probe_serialized)
                _atomic_write_text(Path(entry["path"]), content)
            except OSError as exc:
                entry["status"] = "failed"
                entry["error"] = str(exc)
                changed = True
        if not changed:
            break

    payload["publication_status"] = _publication_status_for_entries(entries)
    payload["runtime_file_writes"] = [
        {"path": entry["path"], "status": entry["status"], "error": entry["error"]}
        for entry in entries
    ]
    if payload["publication_status"] == "failed":
        return payload, 1
    return payload, 0


def _build_combo_runtime_result(
    runtime_state: dict[str, Any],
    resolved_payload: dict[str, Any],
    endpoints: dict[str, str],
) -> dict[str, Any]:
    runtime_config = runtime_state.get("runtime_config", {})
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    combo_manifest = runtime_state.get("combo_manifest", runtime_state)
    services = combo_manifest.get("services", {}) if isinstance(combo_manifest, dict) else {}

    result: dict[str, Any] = {
        "instance_id": resolved_payload.get("instance_id"),
        "status": "ready",
        "resolved_at": _timestamp_now(),
        "gpu_type": resolved_payload.get("gpu_type") or resolved_payload.get("gpu_name"),
        "cost_per_hour": resolved_payload.get("cost_per_hour") or resolved_payload.get("dph"),
        "snapshot_version": str(runtime_config.get("snapshot_version", "")),
        "idle_timeout": runtime_config.get("idle_timeout_seconds"),
    }
    if isinstance(services, dict):
        for service_name in sorted(services.keys()):
            result[f"{service_name}_url"] = endpoints.get(f"{service_name}_url")
    return result


def _resolve_and_publish_combo_runtime(
    provider: Any,
    runtime_state: dict[str, Any],
    instance_id: str,
    *,
    initial_payload: dict[str, Any] | None = None,
    extra_runtime_file_paths: list[str] | None = None,
    runtime_paths_override: list[Path] | None = None,
    allow_restart: bool,
    restart_transition_extra_seconds: float = 0.0,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], int]:
    combo_manifest = runtime_state.get("combo_manifest", runtime_state)
    runtime_config = runtime_state.get("runtime_config", {})
    if not isinstance(runtime_config, dict):
        runtime_config = {}

    resolved_payload, endpoints, health_payload = _resolve_combo_runtime(
        provider,
        instance_id,
        combo_manifest if isinstance(combo_manifest, dict) else {},
        runtime_config,
        initial_payload=initial_payload,
        allow_restart=allow_restart,
        restart_transition_extra_seconds=restart_transition_extra_seconds,
        status_callback=status_callback,
    )

    result = _build_combo_runtime_result(runtime_state, resolved_payload, endpoints)
    combo_name = str(runtime_state.get("combo_name") or runtime_config.get("name") or "runtime")
    probe_payload = None
    if combo_name == "neuroflow":
        result, probe_payload = _build_neuroflow_runtime_bundle(
            runtime_state,
            result,
            health_payload if isinstance(health_payload, dict) else {},
        )
    runtime_paths = (
        list(runtime_paths_override)
        if runtime_paths_override is not None
        else _resolve_runtime_file_paths(
            runtime_config,
            extra_runtime_file_paths,
            combo_name,
        )
    )
    if status_callback is not None:
        if len(runtime_paths) == 0:
            status_callback("Runtime ready. No runtime file publication requested.")
        else:
            status_callback(
                "Runtime ready. Publishing runtime record to "
                + ", ".join(str(path) for path in runtime_paths)
            )
    return _publish_runtime_record(result, runtime_paths, probe_payload=probe_payload)


def _create_combo_instance(
    provider: Any,
    runtime_state: dict[str, Any],
    combo_name: str,
) -> dict[str, Any]:
    runtime_config = runtime_state.get("runtime_config", {})
    if not isinstance(runtime_config, dict):
        runtime_config = {}

    raw_bootstrap_script = str(runtime_state.get("bootstrap_script", ""))
    bootstrap_env = _build_combo_bootstrap_env(runtime_state)
    rendered_bootstrap_script = render_bootstrap_script(
        raw_bootstrap_script,
        bootstrap_env,
    )

    instance_config: dict[str, Any] = {
        "bootstrap_script": rendered_bootstrap_script,
        "ports": runtime_state.get("ports", {}),
        "combo_name": str(runtime_state.get("combo_name") or combo_name),
    }
    if isinstance(runtime_config.get("image"), str) and runtime_config.get("image"):
        instance_config["image"] = str(runtime_config["image"])
    if isinstance(runtime_config.get("bootstrap_base_url"), str) and runtime_config.get(
        "bootstrap_base_url"
    ):
        instance_config["bootstrap_base_url"] = str(runtime_config["bootstrap_base_url"])
    instance_config["runtime_config"] = {
        "bootstrap_base_url": runtime_config.get("bootstrap_base_url")
    }
    if runtime_config.get("min_disk_gb") is not None:
        instance_config["disk"] = runtime_config["min_disk_gb"]
    instance_env = dict(bootstrap_env)
    if runtime_config.get("idle_timeout_seconds") is not None:
        instance_env["IDLE_TIMEOUT_SECONDS"] = str(runtime_config["idle_timeout_seconds"])
    if instance_env:
        instance_config["env"] = instance_env

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
    return created_payload


def _resolve_runtime_state_from_args(combo_name: str, config_path: str | None) -> dict[str, Any]:
    base_config = _maybe_load_combo_base_config(config_path)
    return resolve_runtime_state_for_combo(
        combos_root=DEFAULT_COMBOS_ROOT,
        combo_name=combo_name,
        base_config=base_config,
        cli_overrides={},
    )


def _provider_for_runtime_state(runtime_state: dict[str, Any]) -> VastProvider:
    runtime_config = runtime_state.get("runtime_config", {})
    if not isinstance(runtime_config, dict):
        runtime_config = {}
    return VastProvider(
        api_key=str(runtime_config.get("vast_api_key", "")),
        base_url=str(runtime_config.get("vast_api_url", "https://console.vast.ai/api/v0")),
    )


def _combo_label_for_name(combo_name: str) -> str:
    return f"ai-orch:{combo_name}"


def _wizard_sort_key(combo_name: str, payload: dict[str, Any]) -> tuple[int, tuple[int, str], str]:
    label = str(payload.get("label", ""))
    label_rank = 0 if label == _combo_label_for_name(combo_name) else 1
    status = _normalize_instance_status(payload)
    return (label_rank, _status_sort_key(status), str(payload.get("instance_id", "")))


def _print_combo_menu(combo_names: list[str]) -> None:
    print("Available combos:")
    for index, combo_name in enumerate(combo_names, start=1):
        print(f"  {index}. {combo_name}")


def _read_wizard_input(prompt: str, *, allow_back: bool = False) -> str:
    try:
        raw_value = input(prompt)
    except (EOFError, KeyboardInterrupt) as exc:
        raise _WizardCancelled from exc

    normalized = raw_value.strip()
    lowered = normalized.lower()
    if lowered in {"q", "quit", "exit"}:
        raise _WizardCancelled
    if allow_back and lowered in {"b", "back"}:
        raise _WizardBack
    return normalized


def _prompt_numeric_choice(
    prompt: str,
    minimum: int,
    maximum: int,
    *,
    allow_back: bool = False,
) -> int:
    while True:
        raw_value = _read_wizard_input(prompt, allow_back=allow_back)
        try:
            numeric_value = int(raw_value)
        except ValueError:
            controls = f"Enter a number between {minimum} and {maximum}."
            if allow_back:
                controls += " Use 'b' to go back or 'q' to quit."
            else:
                controls += " Use 'q' to quit."
            print(controls)
            continue
        if minimum <= numeric_value <= maximum:
            return numeric_value
        controls = f"Enter a number between {minimum} and {maximum}."
        if allow_back:
            controls += " Use 'b' to go back or 'q' to quit."
        else:
            controls += " Use 'q' to quit."
        print(controls)


def _select_combo_name_interactively(requested_combo: str | None) -> str:
    if isinstance(requested_combo, str) and requested_combo.strip() != "":
        return requested_combo.strip()
    combo_names = _discover_combo_names(DEFAULT_COMBOS_ROOT)
    if len(combo_names) == 0:
        raise ValueError("No combos found under combos/")
    _print_combo_menu(combo_names)
    choice = _prompt_numeric_choice("Select combo number: ", 1, len(combo_names))
    return combo_names[choice - 1]


def _wizard_status_class(status: str) -> str:
    if status == "running":
        return "running"
    if status in _STARTABLE_INSTANCE_STATES:
        return "restartable"
    if status in _TRANSITIONAL_INSTANCE_STATES:
        return "transitioning"
    if status in _UNAVAILABLE_INSTANCE_STATES:
        return "unavailable"
    return "other"


def _print_instance_menu(combo_name: str, instances: list[dict[str, Any]]) -> None:
    print("")
    print(f"Instances for combo {combo_name}:")
    print("  0. Start new instance")
    for index, payload in enumerate(instances, start=1):
        status = _normalize_instance_status(payload)
        print(
            "  "
            f"{index}. "
            f"id={payload.get('instance_id', '')} "
            f"status={status} ({_wizard_status_class(status)}) "
            f"gpu={payload.get('gpu_name', '') or payload.get('gpu_type', '')} "
            f"ip={payload.get('public_ipaddr', '') or '-'} "
            f"label={payload.get('label', '') or '-'}"
        )


def _prompt_runtime_path_list(prompt: str, *, allow_back: bool = False) -> list[str]:
    raw_value = _read_wizard_input(prompt, allow_back=allow_back)
    if raw_value == "":
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip() != ""]


def _print_runtime_file_paths(runtime_paths: list[Path], *, title: str = "Runtime file output paths:") -> None:
    print("")
    if len(runtime_paths) == 0:
        print("No runtime file output paths configured.")
        return
    print(title)
    for path in runtime_paths:
        print(f"  - {path}")


def _prompt_runtime_file_paths(
    runtime_config: dict[str, Any],
    combo_name: str,
    cli_runtime_paths: list[str],
) -> list[Path]:
    configured_paths = _resolve_runtime_file_paths(
        runtime_config,
        cli_runtime_paths,
        combo_name,
    )
    default_path = _default_runtime_file_path(combo_name)

    while True:
        if configured_paths:
            _print_runtime_file_paths(configured_paths)
            print("Select runtime file handling:")
            print("  1. Use current destinations")
            print("  2. Add extra destinations")
            print("  3. Continue without writing runtime file")
            choice = _prompt_numeric_choice(
                "Select runtime file option: ",
                1,
                3,
                allow_back=True,
            )
            if choice == 1:
                return configured_paths
            if choice == 2:
                extra_paths = _prompt_runtime_path_list(
                    "Add extra runtime file paths (comma-separated): ",
                    allow_back=True,
                )
                if len(extra_paths) == 0:
                    print("No extra runtime file paths entered.")
                    continue
                return _resolve_runtime_file_paths(
                    runtime_config,
                    cli_runtime_paths + extra_paths,
                    combo_name,
                )
            return []

        print("")
        print("No runtime file output paths configured.")
        print(f"Default runtime file location: {default_path}")
        print("Select runtime file handling:")
        print("  1. Use default runtime file location")
        print("  2. Enter custom destination(s)")
        print("  3. Continue without writing runtime file")
        choice = _prompt_numeric_choice(
            "Select runtime file option: ",
            1,
            3,
            allow_back=True,
        )
        if choice == 1:
            return [default_path]
        if choice == 2:
            custom_paths = _prompt_runtime_path_list(
                "Enter runtime file paths (comma-separated): ",
                allow_back=True,
            )
            if len(custom_paths) == 0:
                print("No runtime file paths entered.")
                continue
            return _resolve_runtime_file_paths(
                {},
                custom_paths,
                combo_name,
            )
        return []


def _print_publication_summary(result: dict[str, Any]) -> None:
    print("")
    print(f"Publication status: {result.get('publication_status', 'unknown')}")
    for entry in result.get("runtime_file_writes", []):
        print(
            "  "
            f"{entry.get('status', 'unknown')}: {entry.get('path', '')}"
            f"{' (' + str(entry.get('error')) + ')' if entry.get('error') else ''}"
        )


def _build_wizard_progress_printer() -> Callable[[str], None]:
    inline_active = False
    transient_prefixes = (
        "Waiting for restarted instance ",
        "Waiting for instance ",
        "Waiting for public port mappings ",
        "Waiting for control health endpoint ",
        "Waiting for services to report healthy:",
    )

    def _emit(message: str) -> None:
        nonlocal inline_active
        is_transient = any(message.startswith(prefix) for prefix in transient_prefixes)
        if is_transient and sys.stdout.isatty():
            rendered = f"\r{message}"
            print(rendered.ljust(140), end="", flush=True)
            inline_active = True
            return

        if inline_active:
            print("", flush=True)
            inline_active = False
        print(message, flush=True)

    return _emit


def _prompt_restart_transition_remediation(instance_id: str) -> str:
    print("")
    print(f"Restarted instance {instance_id} is still not runnable.")
    print("Select remediation:")
    print("  1. Destroy this instance and start a new one (Recommended)")
    print("  2. Start a new instance and keep this one")
    print("  3. Wait 5 more minutes")
    print("  4. Back out of this instance and return to instance selection")
    choice = _prompt_numeric_choice(
        "Select remediation option: ",
        1,
        4,
    )
    if choice == 1:
        return "destroy_and_start_new"
    if choice == 2:
        return "start_new_keep_old"
    if choice == 3:
        return "wait_more"
    return "back_to_instances"


def run_combo_start(args) -> int:
    try:
        runtime_state = _resolve_runtime_state_from_args(str(args.combo), args.config)
        provider = _provider_for_runtime_state(runtime_state)

        existing_instances = provider.list_instances()
        if _has_active_instances(existing_instances) and not bool(args.allow_multiple):
            print(
                "Start blocked: existing instance detected. Use --allow-multiple to continue.",
                file=sys.stderr,
            )
            return 1

        created_payload = _create_combo_instance(provider, runtime_state, str(args.combo))
        instance_id = created_payload.get("instance_id")
        if instance_id in (None, ""):
            raise ValueError("Provider create_instance response missing instance_id")

        result, exit_code = _resolve_and_publish_combo_runtime(
            provider,
            runtime_state,
            str(instance_id),
            initial_payload=created_payload,
            extra_runtime_file_paths=getattr(args, "runtime_file_paths", []),
            allow_restart=False,
        )
        print(format_json_output(result), end="")
        return exit_code
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


def run_combo_resolve(args) -> int:
    try:
        runtime_state = _resolve_runtime_state_from_args(str(args.combo), args.config)
        provider = _provider_for_runtime_state(runtime_state)
        polled_payload = provider.poll_instance(str(args.instance_id))
        result, exit_code = _resolve_and_publish_combo_runtime(
            provider,
            runtime_state,
            str(args.instance_id),
            initial_payload=polled_payload,
            extra_runtime_file_paths=getattr(args, "runtime_file_paths", []),
            allow_restart=True,
        )
        print(format_json_output(result), end="")
        return exit_code
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except VastProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1
    except _RestartTransitionTimeout as exc:
        print(f"Resolve error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Resolve error: {exc}", file=sys.stderr)
        return 1


def run_combo_wizard(args) -> int:
    if not sys.stdin.isatty():
        print("Wizard requires an interactive terminal.", file=sys.stderr)
        return 1

    try:
        requested_combo = getattr(args, "combo", None)
        combo_name: str | None = None

        while True:
            if combo_name is None:
                combo_name = _select_combo_name_interactively(requested_combo)

            runtime_state = _resolve_runtime_state_from_args(combo_name, args.config)
            provider = _provider_for_runtime_state(runtime_state)
            progress_printer = _build_wizard_progress_printer()
            listed_instances = provider.list_instances()
            normalized_instances = [
                _instance_to_payload(instance) if not isinstance(instance, dict) else dict(instance)
                for instance in listed_instances
            ]
            ordered_instances = sorted(
                normalized_instances,
                key=lambda payload: _wizard_sort_key(combo_name, payload),
            )

            while True:
                _print_instance_menu(combo_name, ordered_instances)
                try:
                    selection = _prompt_numeric_choice(
                        "Select instance number: ",
                        0,
                        len(ordered_instances),
                        allow_back=requested_combo in (None, ""),
                    )
                except _WizardBack:
                    combo_name = None
                    break

                if selection == 0:
                    selected_payload = _create_combo_instance(provider, runtime_state, combo_name)
                    instance_id = str(selected_payload.get("instance_id", ""))
                    allow_restart = False
                else:
                    selected_payload = dict(ordered_instances[selection - 1])
                    instance_id = str(selected_payload.get("instance_id", ""))
                    allow_restart = True

                while True:
                    try:
                        runtime_paths = _prompt_runtime_file_paths(
                            runtime_state.get("runtime_config", {}),
                            combo_name,
                            list(getattr(args, "runtime_file_paths", [])),
                        )
                    except _WizardBack:
                        break

                    active_instance_id = instance_id
                    active_payload = selected_payload
                    active_allow_restart = allow_restart
                    restart_transition_extra_seconds = 0.0
                    return_to_instance_selection = False

                    while True:
                        try:
                            result, exit_code = _resolve_and_publish_combo_runtime(
                                provider,
                                runtime_state,
                                active_instance_id,
                                initial_payload=active_payload,
                                allow_restart=active_allow_restart,
                                runtime_paths_override=runtime_paths,
                                restart_transition_extra_seconds=restart_transition_extra_seconds,
                                status_callback=progress_printer,
                            )
                            _print_publication_summary(result)
                            print("")
                            print(format_json_output(result))
                            return exit_code
                        except _RestartTransitionTimeout as exc:
                            print("")
                            print(str(exc))
                            remediation = _prompt_restart_transition_remediation(active_instance_id)
                            if remediation == "destroy_and_start_new":
                                print(
                                    f"Destroying stuck instance {active_instance_id} and starting a new one...",
                                    flush=True,
                                )
                                provider.destroy_instance(str(active_instance_id))
                                active_payload = _create_combo_instance(provider, runtime_state, combo_name)
                                active_instance_id = str(active_payload.get("instance_id", ""))
                                active_allow_restart = False
                                restart_transition_extra_seconds = 0.0
                                continue
                            if remediation == "start_new_keep_old":
                                print(
                                    f"Starting a new instance while keeping {active_instance_id}...",
                                    flush=True,
                                )
                                active_payload = _create_combo_instance(provider, runtime_state, combo_name)
                                active_instance_id = str(active_payload.get("instance_id", ""))
                                active_allow_restart = False
                                restart_transition_extra_seconds = 0.0
                                continue
                            if remediation == "wait_more":
                                restart_transition_extra_seconds += 300.0
                                active_payload = dict(exc.payload)
                                print(
                                    f"Extending restart wait budget by 300 seconds for instance {active_instance_id}...",
                                    flush=True,
                                )
                                continue
                            return_to_instance_selection = True
                            break

                    if return_to_instance_selection:
                        break

                continue

            if combo_name is None:
                continue
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except VastProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1
    except _WizardCancelled:
        print("Wizard cancelled.", file=sys.stderr)
        return 130
    except ValueError as exc:
        print(f"Wizard error: {exc}", file=sys.stderr)
        return 1


def run_combos_command() -> int:
    combo_names = _discover_combo_names(DEFAULT_COMBOS_ROOT)
    if len(combo_names) == 0:
        print("No combos found.")
        return 0
    _print_combo_menu(combo_names)
    return 0


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
    normalized_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if len(normalized_argv) == 0:
        parser.print_help()
        return 0
    args = parser.parse_args(normalized_argv)

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

    if args.command == "combos":
        return run_combos_command()
    if args.command == "wizard":
        return run_combo_wizard(args)
    if args.command == "resolve":
        return run_combo_resolve(args)
    if args.command != "start":
        return 1
    if getattr(args, "combo", None):
        return run_combo_start(args)
    return run_legacy_start(args)
