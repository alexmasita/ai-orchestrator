import copy
import importlib

import pytest


INTERFACE_MODULE = "ai_orchestrator.provider.interface"
ORCHESTRATOR_MODULE = "ai_orchestrator.orchestrator"


def _load_interface_module():
    return importlib.import_module(INTERFACE_MODULE)


def _load_orchestrator_module():
    return importlib.import_module(ORCHESTRATOR_MODULE)


def _offers():
    interface = _load_interface_module()
    return [
        interface.ProviderOffer(
            id="offer-a",
            gpu_name="RTX_4090",
            gpu_ram_gb=24,
            reliability=0.96,
            dph=1.00,
            inet_up_mbps=200.0,
            inet_down_mbps=400.0,
            interruptible=False,
            disk_gb=120.0,
        ),
        interface.ProviderOffer(
            id="offer-b",
            gpu_name="A100",
            gpu_ram_gb=80,
            reliability=0.99,
            dph=1.20,
            inet_up_mbps=800.0,
            inet_down_mbps=800.0,
            interruptible=False,
            disk_gb=320.0,
        ),
        interface.ProviderOffer(
            id="offer-c",
            gpu_name="L40S",
            gpu_ram_gb=48,
            reliability=0.95,
            dph=0.95,
            inet_up_mbps=100.0,
            inet_down_mbps=150.0,
            interruptible=True,
            disk_gb=80.0,
        ),
    ]


def _base_config():
    return {
        "min_reliability": 0.90,
        "min_inet_up_mbps": 100.0,
        "min_inet_down_mbps": 100.0,
        "allow_interruptible": True,
        "max_dph": 2.00,
    }


def test_selection_filters_by_gpu_ram_gb():
    orch = _load_orchestrator_module()
    selected = orch.select_offer(_offers(), required_vram_gb=70, config=_base_config())
    assert selected.id == "offer-b"


def test_selection_filters_by_reliability():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["min_reliability"] = 0.98
    selected = orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
    assert selected.id == "offer-b"


def test_selection_filters_by_min_inet_up_mbps():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["min_inet_up_mbps"] = 700.0
    selected = orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
    assert selected.id == "offer-b"


def test_selection_filters_by_min_inet_down_mbps():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["min_inet_down_mbps"] = 700.0
    selected = orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
    assert selected.id == "offer-b"


def test_selection_respects_interruptible_policy():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["allow_interruptible"] = False
    selected = orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
    assert selected.id == "offer-a"


def test_selection_filters_by_max_dph():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["max_dph"] = 1.00
    selected = orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
    assert selected.id == "offer-c"


def test_selection_filters_by_min_disk_gb():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["min_disk_gb"] = 300.0
    selected = orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
    assert selected.id == "offer-b"


def test_selection_sorting_order_dph_then_reliability_then_gpu_name():
    interface = _load_interface_module()
    orch = _load_orchestrator_module()
    offers = [
        interface.ProviderOffer(
            id="offer-x",
            gpu_name="ZetaGPU",
            gpu_ram_gb=32,
            reliability=0.98,
            dph=1.00,
            inet_up_mbps=500.0,
            inet_down_mbps=500.0,
            interruptible=False,
            disk_gb=500.0,
        ),
        interface.ProviderOffer(
            id="offer-y",
            gpu_name="AlphaGPU",
            gpu_ram_gb=32,
            reliability=0.99,
            dph=1.00,
            inet_up_mbps=500.0,
            inet_down_mbps=500.0,
            interruptible=False,
            disk_gb=500.0,
        ),
    ]
    selected = orch.select_offer(offers, required_vram_gb=1, config=_base_config())
    assert selected.id == "offer-y"


def test_selection_explicit_tie_breaker_gpu_name_asc():
    interface = _load_interface_module()
    orch = _load_orchestrator_module()
    offers = [
        interface.ProviderOffer(
            id="offer-1",
            gpu_name="BetaGPU",
            gpu_ram_gb=40,
            reliability=0.97,
            dph=1.50,
            inet_up_mbps=500.0,
            inet_down_mbps=500.0,
            interruptible=False,
            disk_gb=500.0,
        ),
        interface.ProviderOffer(
            id="offer-2",
            gpu_name="AlphaGPU",
            gpu_ram_gb=40,
            reliability=0.97,
            dph=1.50,
            inet_up_mbps=500.0,
            inet_down_mbps=500.0,
            interruptible=False,
            disk_gb=500.0,
        ),
    ]
    selected = orch.select_offer(offers, required_vram_gb=1, config=_base_config())
    assert selected.id == "offer-2"


def test_selection_is_deterministic_across_repeated_calls():
    orch = _load_orchestrator_module()
    offers = _offers()
    cfg = _base_config()
    first = orch.select_offer(offers, required_vram_gb=1, config=cfg).id
    second = orch.select_offer(offers, required_vram_gb=1, config=cfg).id
    third = orch.select_offer(offers, required_vram_gb=1, config=cfg).id
    assert first == second == third


def test_selection_does_not_mutate_input_offer_list():
    orch = _load_orchestrator_module()
    offers = _offers()
    original = copy.deepcopy(offers)
    orch.select_offer(offers, required_vram_gb=1, config=_base_config())
    assert offers == original


def test_selection_is_independent_from_input_ordering():
    orch = _load_orchestrator_module()
    offers = _offers()
    reversed_offers = list(reversed(offers))
    cfg = _base_config()
    a = orch.select_offer(offers, required_vram_gb=1, config=cfg).id
    b = orch.select_offer(reversed_offers, required_vram_gb=1, config=cfg).id
    assert a == b


def test_selection_raises_offer_selection_error_when_no_offers_match():
    orch = _load_orchestrator_module()
    cfg = _base_config()
    cfg["max_dph"] = 0.1
    with pytest.raises(orch.OfferSelectionError):
        orch.select_offer(_offers(), required_vram_gb=1, config=cfg)


@pytest.mark.parametrize(
    "missing_key",
    [
        "min_reliability",
        "min_inet_up_mbps",
        "min_inet_down_mbps",
        "allow_interruptible",
        "max_dph",
    ],
)
def test_selection_missing_required_config_fields_raise_key_error(missing_key):
    orch = _load_orchestrator_module()
    cfg = _base_config()
    del cfg[missing_key]
    with pytest.raises(KeyError):
        orch.select_offer(_offers(), required_vram_gb=1, config=cfg)
