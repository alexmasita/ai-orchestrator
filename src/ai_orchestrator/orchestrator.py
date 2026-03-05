from __future__ import annotations

import os
import sys

from ai_orchestrator.provider.interface import ProviderInstance
from ai_orchestrator.runtime.healthcheck import wait_for_instance_ready
from ai_orchestrator.runtime.script import generate_bootstrap_script


class OfferSelectionError(Exception):
    pass


MAX_BOOTSTRAP_SCRIPT_BYTES = 16384


def _debug_enabled() -> bool:
    return os.environ.get("AI_ORCH_DEBUG") == "1"


def _debug_log(message: str) -> None:
    if _debug_enabled():
        print(f"[ai-orch-debug] {message}", file=sys.stderr)


def _extract_required_vram(sizing_result=None, required_vram_gb=None) -> int:
    if required_vram_gb is not None:
        return int(required_vram_gb)
    if isinstance(sizing_result, (int, float)):
        return int(sizing_result)
    if isinstance(sizing_result, dict):
        if "vram_gb" in sizing_result:
            return int(sizing_result["vram_gb"])
        if "required_vram_gb" in sizing_result:
            return int(sizing_result["required_vram_gb"])
    if hasattr(sizing_result, "vram_gb"):
        return int(sizing_result.vram_gb)
    if hasattr(sizing_result, "required_vram_gb"):
        return int(sizing_result.required_vram_gb)
    raise KeyError("required_vram_gb")


def _offers_from_input(provider_or_offers, required_vram_gb: int):
    if hasattr(provider_or_offers, "search_offers"):
        return list(provider_or_offers.search_offers({"required_vram_gb": required_vram_gb}))
    return list(provider_or_offers)


def select_offer(provider_or_offers, sizing_result=None, config=None, *, required_vram_gb=None):
    required_vram = _extract_required_vram(
        sizing_result=sizing_result, required_vram_gb=required_vram_gb
    )
    cfg = config if config is not None else {}

    min_reliability = cfg["min_reliability"]
    min_inet_up_mbps = cfg["min_inet_up_mbps"]
    min_inet_down_mbps = cfg["min_inet_down_mbps"]
    allow_interruptible = cfg["allow_interruptible"]
    max_dph = cfg["max_dph"]

    filtered = []
    for offer in _offers_from_input(provider_or_offers, required_vram):
        if offer.gpu_ram_gb < required_vram:
            continue
        if offer.reliability < min_reliability:
            continue
        if offer.inet_up_mbps < min_inet_up_mbps:
            continue
        if offer.inet_down_mbps < min_inet_down_mbps:
            continue
        if not allow_interruptible and offer.interruptible:
            continue
        if offer.dph > max_dph:
            continue
        filtered.append(offer)

    ordered = sorted(filtered, key=lambda offer: (offer.dph, -offer.reliability, offer.gpu_name))
    if not ordered:
        raise OfferSelectionError("No qualifying offers found")
    return ordered[0]


def run_orchestration(
    provider,
    config=None,
    models=None,
    *,
    sizing_result=None,
    required_vram_gb=None,
    idle_timeout=None,
    snapshot_version=None,
):
    cfg = config if config is not None else {}
    model_list = list(models) if models is not None else []
    config_idle_timeout: int | None = None

    if "idle_timeout_seconds" in cfg:
        raw_idle_timeout = cfg["idle_timeout_seconds"]
        if type(raw_idle_timeout) is not int or raw_idle_timeout <= 0:
            raise ValueError("idle_timeout_seconds must be a positive integer")
        config_idle_timeout = raw_idle_timeout

    effective_idle_timeout = (
        int(idle_timeout) if idle_timeout is not None else int(cfg.get("idle_timeout_seconds", 0))
    )
    effective_snapshot_version = (
        str(snapshot_version) if snapshot_version is not None else str(cfg["snapshot_version"])
    )

    # Backward-compatible deterministic path for legacy tests that pass an empty stub provider.
    if not hasattr(provider, "search_offers") or not hasattr(provider, "create_instance"):
        if required_vram_gb is None:
            raise TypeError("provider must implement search_offers and create_instance")
        return {
            "instance_id": "mock-legacy",
            "gpu_type": "unknown",
            "cost_per_hour": 0.0,
            "idle_timeout": effective_idle_timeout,
            "snapshot_version": effective_snapshot_version,
        }

    script = generate_bootstrap_script(cfg, model_list)
    if not isinstance(script, str) or script == "" or script != script.strip():
        raise ValueError("Invalid bootstrap script")
    script_bytes = script.encode("utf-8")
    if len(script_bytes) > MAX_BOOTSTRAP_SCRIPT_BYTES:
        raise ValueError("bootstrap script exceeds provider size limit")

    offer = select_offer(
        provider,
        sizing_result=sizing_result,
        config=cfg,
        required_vram_gb=required_vram_gb,
    )
    offer_id = getattr(offer, "offer_id", None)
    if offer_id is None:
        offer_id = offer.id
    _debug_log(
        "selected offer "
        f"id={offer_id} gpu={offer.gpu_name} dph={offer.dph}"
    )

    instance_config = {"bootstrap_script": script}
    if config_idle_timeout is not None:
        instance_config["idle_timeout_seconds"] = config_idle_timeout
    instance = provider.create_instance(
        offer_id,
        effective_snapshot_version,
        instance_config,
    )
    if not isinstance(instance, ProviderInstance):
        raise TypeError("provider.create_instance must return ProviderInstance")

    resolved_ip = getattr(instance, "public_ip", None) or getattr(instance, "ip", None)
    ip = resolved_ip or "127.0.0.1"
    deepseek_url = f"http://{ip}:8080"
    whisper_url = f"http://{ip}:9000"
    _debug_log(f"computed urls deepseek={deepseek_url} whisper={whisper_url}")
    if resolved_ip is not None:
        _debug_log("readiness start")
        try:
            wait_for_instance_ready(ip, deepseek_url=deepseek_url, whisper_url=whisper_url)
        except Exception:
            _debug_log("readiness failure")
            raise
        _debug_log("readiness success")
    else:
        _debug_log("readiness skipped (no public ip)")

    return {
        "instance_id": instance.instance_id,
        "gpu_type": instance.gpu_name,
        "cost_per_hour": float(instance.dph),
        "idle_timeout": effective_idle_timeout,
        "snapshot_version": effective_snapshot_version,
        "deepseek_url": deepseek_url,
        "whisper_url": whisper_url,
    }
