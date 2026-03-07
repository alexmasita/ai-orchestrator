from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceRegistry:
    services: dict[str, dict[str, Any]]

    @classmethod
    def from_combo_manifest(cls, manifest: dict[str, Any]) -> "ServiceRegistry":
        raw_services = manifest.get("services", {})
        if not isinstance(raw_services, dict):
            raw_services = {}

        normalized: dict[str, dict[str, Any]] = {}
        for service_name in sorted(raw_services.keys()):
            service = raw_services.get(service_name)
            if not isinstance(service, dict):
                service = {}
            normalized[service_name] = {
                "port": service.get("port"),
                "health_path": service.get("health_path", "/health"),
            }
        return cls(services=normalized)

    def service_names(self) -> list[str]:
        return list(self.services.keys())

    def aggregate_health(self, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        known_results: dict[str, dict[str, Any]] = {}
        down_services: list[str] = []

        for service_name in self.service_names():
            raw_service_result = results.get(service_name, {})
            status = str(raw_service_result.get("status", "down"))
            known_results[service_name] = {"status": status}
            if status != "up":
                down_services.append(service_name)

        if len(known_results) == 0:
            overall_status = "down"
        elif len(down_services) == 0:
            overall_status = "up"
        elif len(down_services) == len(known_results):
            overall_status = "down"
        else:
            overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "down_services": down_services,
            "services": known_results,
        }
