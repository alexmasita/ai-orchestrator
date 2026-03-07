from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderOffer:
    id: str
    gpu_name: str
    gpu_ram_gb: int
    reliability: float
    dph: float
    inet_up_mbps: float
    inet_down_mbps: float
    interruptible: bool


@dataclass
class ProviderInstance:
    instance_id: str
    gpu_name: str
    dph: float
    public_ip: str | None = None


class Provider(ABC):
    @abstractmethod
    def search_offers(self, requirements: Any):
        pass

    @abstractmethod
    def create_instance(
        self,
        offer_id: str,
        snapshot_version: str,
        instance_config: Any | None = None,
    ):
        pass

    def poll_instance(self, instance_id: str):
        raise NotImplementedError

    def list_instances(self):
        raise NotImplementedError

    def set_instance_state(self, instance_id: str, state: str):
        raise NotImplementedError

    def destroy_instance(self, instance_id: str):
        raise NotImplementedError
