from __future__ import annotations

import os
import sys
import time
from typing import Any

from ai_orchestrator.provider.interface import Provider
from ai_orchestrator.provider.interface import ProviderInstance, ProviderOffer

try:
    import requests
except Exception:  # pragma: no cover - test suite monkeypatches requests
    requests = None

INSTANCE_READY_POLL_INTERVAL_SECONDS = 2
INSTANCE_READY_TIMEOUT_SECONDS_DEFAULT = 180


class VastProviderError(Exception):
    pass


def _debug_enabled() -> bool:
    return os.environ.get("AI_ORCH_DEBUG") == "1"


def _debug_log(message: str) -> None:
    if _debug_enabled():
        print(f"[ai-orch-debug] {message}", file=sys.stderr)


class VastProvider(Provider):
    _SUPPORTED_REQUIREMENTS_KEYS = {
        "required_vram_gb",
        "max_dph",
        "min_reliability",
        "min_inet_up_mbps",
        "min_inet_down_mbps",
        "verified_only",
        "require_rentable",
        "allow_interruptible",
        "min_duration_seconds",
        "instance_ready_timeout_seconds",
        "limit",
    }
    _MAX_RETRY_CONTEXT_ENTRIES = 512

    def __init__(self, api_key: str, base_url: str = "https://console.vast.ai/api/v0"):
        self.api_key = api_key
        self.base_url = str(base_url).strip().rstrip("/")
        self._offer_requirements_context: dict[str, dict[str, Any]] = {}
        self._offer_requirements_order: list[str] = []
        self._ensure_requests_available()

    @staticmethod
    def _ensure_requests_available():
        if requests is None:
            raise VastProviderError("requests dependency is missing; install with pip install -e .")

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _request_exception_type():
        exceptions = getattr(requests, "exceptions", None)
        if exceptions is not None and hasattr(exceptions, "RequestException"):
            return exceptions.RequestException
        return Exception

    @staticmethod
    def _response_error_detail(response: Any) -> str:
        detail = ""
        try:
            payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            msg = payload.get("msg")
            err = payload.get("error")
            message = payload.get("message")
            extra_detail = payload.get("detail")
            parts = [
                str(value)
                for value in (msg, err, message, extra_detail)
                if value not in (None, "")
            ]
            if parts:
                detail = " ".join(parts)

        if detail == "":
            text = getattr(response, "text", "")
            if isinstance(text, str):
                detail = text.strip()

        return detail[:200]

    @staticmethod
    def _is_no_such_ask_message(message: str) -> bool:
        return "no_such_ask" in message.lower()

    @classmethod
    def _raise_for_status(cls, endpoint: str, response: Any, ok_statuses: tuple[int, ...]) -> None:
        if response.status_code in ok_statuses:
            return

        detail = cls._response_error_detail(response)
        if detail:
            raise VastProviderError(
                f"Vast {endpoint} failed: status={response.status_code} msg={detail}"
            )
        raise VastProviderError(f"Vast {endpoint} failed: status={response.status_code}")

    @staticmethod
    def _extract_offers_payload(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and "offers" in payload:
            offers = payload["offers"]
        elif isinstance(payload, list):
            offers = payload
        else:
            raise VastProviderError("Unexpected /bundles response shape")

        if isinstance(offers, dict):
            offers = [offers]
        if not isinstance(offers, list):
            raise VastProviderError("Unexpected /bundles response shape")
        return offers

    @staticmethod
    def _map_offer(item: Any) -> ProviderOffer:
        if not isinstance(item, dict):
            raise VastProviderError("Malformed offer object from Vast API")

        raw_offer_id = item.get("id")
        if isinstance(raw_offer_id, bool) or raw_offer_id is None:
            raise VastProviderError("Malformed offer object from Vast API: missing or invalid id")
        if isinstance(raw_offer_id, int):
            offer_id = raw_offer_id
        elif isinstance(raw_offer_id, str):
            stripped = raw_offer_id.strip()
            if stripped.isdigit():
                offer_id = int(stripped)
            else:
                raise VastProviderError("Malformed offer object from Vast API: missing or invalid id")
        else:
            raise VastProviderError("Malformed offer object from Vast API: missing or invalid id")

        gpu_name = item.get("gpu_name")
        gpu_ram = item.get("gpu_ram")
        dph_value = item.get("dph", item.get("dph_total"))

        if gpu_name is None or gpu_ram is None or dph_value is None:
            raise VastProviderError("Malformed offer object from Vast API")

        reliability = item.get("reliability2", item.get("reliability", 0.0))
        inet_up = item.get("inet_up", 0.0)
        inet_down = item.get("inet_down", 0.0)
        interruptible = item.get("interruptible")
        if interruptible is None:
            interruptible = bool(item.get("is_bid", False))

        return ProviderOffer(
            id=str(int(offer_id)),
            gpu_name=str(gpu_name),
            gpu_ram_gb=int(gpu_ram),
            reliability=float(reliability),
            dph=float(dph_value),
            inet_up_mbps=float(inet_up),
            inet_down_mbps=float(inet_down),
            interruptible=bool(interruptible),
        )

    @staticmethod
    def _extract_instance_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict) and "instances" in payload:
            instance = payload["instances"]
            if isinstance(instance, list):
                if not instance:
                    raise VastProviderError("Malformed instance object from Vast API")
                instance = instance[0]
        else:
            instance = payload

        if not isinstance(instance, dict):
            raise VastProviderError("Malformed instance object from Vast API")
        return instance

    @staticmethod
    def _resolve_public_ip(instance_payload: dict[str, Any]) -> str | None:
        public_ipaddr = instance_payload.get("public_ipaddr")
        public_ip = instance_payload.get("public_ip")
        return public_ipaddr or public_ip

    @staticmethod
    def _resolve_instance_ready_timeout(requirements: dict[str, Any] | None) -> float:
        if not isinstance(requirements, dict):
            return float(INSTANCE_READY_TIMEOUT_SECONDS_DEFAULT)

        raw_timeout = requirements.get(
            "instance_ready_timeout_seconds",
            INSTANCE_READY_TIMEOUT_SECONDS_DEFAULT,
        )
        if isinstance(raw_timeout, bool):
            return float(INSTANCE_READY_TIMEOUT_SECONDS_DEFAULT)
        try:
            timeout_value = float(raw_timeout)
        except (TypeError, ValueError):
            return float(INSTANCE_READY_TIMEOUT_SECONDS_DEFAULT)
        if timeout_value <= 0:
            return float(INSTANCE_READY_TIMEOUT_SECONDS_DEFAULT)
        return timeout_value

    @staticmethod
    def _format_timeout(timeout_seconds: float) -> str:
        return str(int(timeout_seconds)) if timeout_seconds.is_integer() else str(timeout_seconds)

    @staticmethod
    def _parse_required_vram_gb(requirements: dict[str, Any]) -> int:
        if "required_vram_gb" not in requirements:
            raise VastProviderError("required_vram_gb is required")

        raw_value = requirements["required_vram_gb"]
        if isinstance(raw_value, bool):
            raise VastProviderError("required_vram_gb must be an int-like value")
        if isinstance(raw_value, int):
            return raw_value

        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            raise VastProviderError("required_vram_gb must be an int-like value") from None

        if not numeric_value.is_integer():
            raise VastProviderError("required_vram_gb must be an int-like value")
        return int(numeric_value)

    @classmethod
    def _build_bundle_payload(cls, requirements: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(requirements, dict):
            raise VastProviderError("requirements must be a dict")

        unknown_keys = sorted(
            key for key in requirements.keys() if key not in cls._SUPPORTED_REQUIREMENTS_KEYS
        )
        if unknown_keys:
            keys = ", ".join(unknown_keys)
            raise VastProviderError(f"Unsupported requirements keys: {keys}")

        required_vram_gb = cls._parse_required_vram_gb(requirements)
        payload: dict[str, Any] = {
            "gpu_ram": {"gte": required_vram_gb * 1024},
            "rented": {"eq": False},
            "order": [["dph_total", "asc"], ["reliability", "desc"]],
        }

        if "max_dph" in requirements:
            payload["dph_total"] = {"lte": float(requirements["max_dph"])}
        if "min_reliability" in requirements:
            payload["reliability"] = {"gte": float(requirements["min_reliability"])}
        if "min_inet_up_mbps" in requirements:
            payload["inet_up"] = {"gte": float(requirements["min_inet_up_mbps"])}
        if "min_inet_down_mbps" in requirements:
            payload["inet_down"] = {"gte": float(requirements["min_inet_down_mbps"])}

        verified_only = requirements.get("verified_only")
        if verified_only is not None:
            if type(verified_only) is not bool:
                raise VastProviderError("verified_only must be a bool")
            if verified_only:
                payload["verified"] = {"eq": True}

        require_rentable = requirements.get("require_rentable")
        if require_rentable is not None:
            if type(require_rentable) is not bool:
                raise VastProviderError("require_rentable must be a bool")
            if require_rentable:
                payload["rentable"] = {"eq": True}

        allow_interruptible = requirements.get("allow_interruptible")
        if allow_interruptible is not None:
            if type(allow_interruptible) is not bool:
                raise VastProviderError("allow_interruptible must be a bool")
            payload["type"] = "bid" if allow_interruptible else "ondemand"

        if "min_duration_seconds" in requirements:
            payload["duration"] = {"gte": int(requirements["min_duration_seconds"])}

        limit = requirements.get("limit")
        if limit is not None:
            if type(limit) is not int or limit <= 0:
                raise VastProviderError("limit must be a positive int")
            payload["limit"] = limit

        return payload

    def _remember_offer_requirements(self, offer_ids: list[str], requirements: dict[str, Any]) -> None:
        for offer_id in offer_ids:
            if offer_id in self._offer_requirements_context:
                try:
                    self._offer_requirements_order.remove(offer_id)
                except ValueError:
                    pass
            self._offer_requirements_context[offer_id] = dict(requirements)
            self._offer_requirements_order.append(offer_id)
        while len(self._offer_requirements_order) > self._MAX_RETRY_CONTEXT_ENTRIES:
            oldest_offer_id = self._offer_requirements_order.pop(0)
            self._offer_requirements_context.pop(oldest_offer_id, None)

    def _poll_instance_until_ready(
        self,
        contract_id: str,
        timeout_seconds: float,
        request_exc: type[Exception],
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                instance_response = requests.get(
                    self._url(f"instances/{contract_id}"),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            except request_exc as exc:  # pragma: no cover - exercised by tests
                raise VastProviderError(f"Vast /instances request failed: {exc}") from exc
            self._raise_for_status("/instances", instance_response, (200,))

            instance_payload = self._extract_instance_payload(instance_response.json())
            public_ip = self._resolve_public_ip(instance_payload)
            actual_status = instance_payload.get("actual_status")
            if public_ip and (actual_status is None or actual_status == "running"):
                return instance_payload

            if time.monotonic() >= deadline:
                break
            time.sleep(INSTANCE_READY_POLL_INTERVAL_SECONDS)

        timeout_label = self._format_timeout(timeout_seconds)
        raise VastProviderError(
            f"instance did not reach running+ip state within {timeout_label}s"
        )

    def search_offers(self, requirements):
        search_payload = self._build_bundle_payload(requirements)
        request_exc = self._request_exception_type()
        try:
            response = requests.post(
                self._url("bundles"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=search_payload,
            )
        except request_exc as exc:  # pragma: no cover - exercised by tests
            raise VastProviderError(f"Vast /bundles request failed: {exc}") from exc

        self._raise_for_status("/bundles", response, (200,))
        payload: Any = response.json()
        offers = self._extract_offers_payload(payload)
        mapped_offers = [self._map_offer(item) for item in offers]
        self._remember_offer_requirements([offer.id for offer in mapped_offers], dict(requirements))
        return mapped_offers

    def create_instance(
        self,
        offer_id: str,
        snapshot_version: str,
        instance_config: dict[str, Any] | None = None,
    ):
        request_exc = self._request_exception_type()
        if instance_config is None:
            _debug_log(f"create_instance endpoint={self._url('instances')} method=POST")
            try:
                response = requests.post(
                    self._url("instances"),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"offer_id": offer_id, "snapshot_version": snapshot_version},
                )
            except request_exc as exc:  # pragma: no cover - exercised by tests
                raise VastProviderError(f"Vast /instances request failed: {exc}") from exc
            self._raise_for_status("/instances", response, (200, 201))
            payload: dict[str, Any] = response.json()
            return ProviderInstance(
                instance_id=str(payload["instance_id"]),
                gpu_name=str(payload["gpu_name"]),
                dph=float(payload["dph"]),
                public_ip=payload.get("public_ipaddr"),
            )
        else:
            script = instance_config.get("bootstrap_script")
            if not isinstance(script, str) or script == "":
                raise ValueError("Missing bootstrap_script")

            payload = {
                "image": "ubuntu:22.04",
                "runtype": "ssh_direct",
                "env": {
                    "-p 8080:8080": "1",
                    "-p 9000:9000": "1",
                },
                "onstart": script,
            }

            def _create_from_offer_id(target_offer_id: str) -> Any:
                _debug_log(f"create_instance endpoint={self._url(f'asks/{target_offer_id}')} method=PUT")
                try:
                    response = requests.put(
                        self._url(f"asks/{target_offer_id}"),
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                except request_exc as exc:  # pragma: no cover - exercised by tests
                    raise VastProviderError(f"Vast /asks request failed: {exc}") from exc
                self._raise_for_status("/asks", response, (200, 201))
                return response.json()

            original_offer_id = str(offer_id)
            retry_requirements = self._offer_requirements_context.pop(original_offer_id, None)
            try:
                self._offer_requirements_order.remove(original_offer_id)
            except ValueError:
                pass
            try:
                create_payload: Any = _create_from_offer_id(original_offer_id)
            except VastProviderError as original_exc:
                if not self._is_no_such_ask_message(str(original_exc)):
                    raise
                if retry_requirements is None:
                    raise original_exc
                refreshed_offers = self.search_offers(dict(retry_requirements))
                retry_offer_id = None
                for refreshed_offer in refreshed_offers:
                    candidate_id = str(refreshed_offer.id)
                    if candidate_id != original_offer_id:
                        retry_offer_id = candidate_id
                        break
                if retry_offer_id is None:
                    raise original_exc
                self._offer_requirements_context.pop(retry_offer_id, None)
                try:
                    self._offer_requirements_order.remove(retry_offer_id)
                except ValueError:
                    pass
                create_payload = _create_from_offer_id(retry_offer_id)

            if not isinstance(create_payload, dict):
                raise VastProviderError("Instance creation response missing new_contract")
            contract_id = create_payload.get("new_contract")
            if not contract_id:
                raise VastProviderError("Instance creation response missing new_contract")

            ready_timeout_seconds = self._resolve_instance_ready_timeout(retry_requirements)
            instance_payload = self._poll_instance_until_ready(
                str(contract_id),
                ready_timeout_seconds,
                request_exc,
            )
            gpu_name = instance_payload.get("gpu_name")
            dph_value = instance_payload.get("dph_total", instance_payload.get("dph"))
            if gpu_name is None or dph_value is None:
                raise VastProviderError("Malformed instance object from Vast API")

            return ProviderInstance(
                instance_id=str(contract_id),
                gpu_name=str(gpu_name),
                dph=float(dph_value),
                public_ip=self._resolve_public_ip(instance_payload),
            )

    def destroy_instance(self, instance_id: str):
        request_exc = self._request_exception_type()
        try:
            response = requests.delete(
                self._url(f"instances/{instance_id}"),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except request_exc as exc:  # pragma: no cover - exercised by tests
            raise VastProviderError(f"Vast delete request failed: {exc}") from exc
        self._raise_for_status("delete", response, (200,))
