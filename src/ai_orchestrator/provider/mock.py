from __future__ import annotations

from ai_orchestrator.provider.interface import Provider, ProviderInstance, ProviderOffer


class MockProvider(Provider):
    def __init__(self, offers: list[ProviderOffer]):
        self._offers = tuple(offers)

    def search_offers(self, requirements):
        return list(self._offers)

    def create_instance(self, offer_id: str, snapshot_version: str):
        for offer in self._offers:
            if offer.id == offer_id:
                return ProviderInstance(
                    instance_id=f"mock-{offer_id}",
                    gpu_name=offer.gpu_name,
                    dph=float(offer.dph),
                )
        raise KeyError(offer_id)
