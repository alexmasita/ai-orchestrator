from __future__ import annotations

import os
import sys
from typing import Any

from ai_orchestrator.provider.interface import Provider
from ai_orchestrator.provider.interface import ProviderInstance, ProviderOffer

try:
    import requests
except Exception:  # pragma: no cover - test suite monkeypatches requests
    requests = None


class VastProviderError(Exception):
    pass


def _debug_enabled() -> bool:
    return os.environ.get("AI_ORCH_DEBUG") == "1"


def _debug_log(message: str) -> None:
    if _debug_enabled():
        print(f"[ai-orch-debug] {message}", file=sys.stderr)


class VastProvider(Provider):
    def __init__(self, api_key: str, base_url: str = "https://console.vast.ai/api/v0"):
        self.api_key = api_key
        self.base_url = str(base_url).strip().rstrip("/")
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

    def search_offers(self, requirements):
        request_exc = self._request_exception_type()
        try:
            response = requests.get(
                self._url("bundles"),
                headers={"Authorization": f"Bearer {self.api_key}"},
                params=requirements,
            )
        except request_exc as exc:  # pragma: no cover - exercised by tests
            raise VastProviderError(f"Vast /bundles request failed: {exc}") from exc

        if response.status_code != 200:
            raise VastProviderError(f"Vast /bundles failed: status={response.status_code}")

        offers: list[ProviderOffer] = []
        for item in response.json():
            offers.append(
                ProviderOffer(
                    id=item["id"],
                    gpu_name=item["gpu_name"],
                    gpu_ram_gb=item["gpu_ram"],
                    reliability=item["reliability2"],
                    dph=item["dph_total"],
                    inet_up_mbps=item["inet_up"],
                    inet_down_mbps=item["inet_down"],
                    interruptible=item["interruptible"],
                )
            )
        return offers

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
            if response.status_code not in (200, 201):
                raise VastProviderError(f"Vast /instances failed: status={response.status_code}")
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
            _debug_log(f"create_instance endpoint={self._url(f'asks/{offer_id}')} method=PUT")
            try:
                response = requests.put(
                    self._url(f"asks/{offer_id}"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except request_exc as exc:  # pragma: no cover - exercised by tests
                raise VastProviderError(f"Vast /asks request failed: {exc}") from exc
            if response.status_code not in (200, 201):
                raise VastProviderError(f"Vast /asks failed: status={response.status_code}")

        payload: dict[str, Any] = response.json()
        return ProviderInstance(
            instance_id=payload["instance_id"],
            gpu_name=payload["gpu_name"],
            dph=payload["dph"],
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
        if response.status_code != 200:
            raise VastProviderError(f"Vast delete failed: status={response.status_code}")
