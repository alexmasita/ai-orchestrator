import dataclasses
import importlib
import inspect


INTERFACE_MODULE = "ai_orchestrator.provider.interface"


def _load_interface_module():
    return importlib.import_module(INTERFACE_MODULE)


def test_provider_interface_module_import_path():
    module = _load_interface_module()
    assert module.__name__ == INTERFACE_MODULE


def test_provider_offer_dataclass_exists_with_exact_fields():
    module = _load_interface_module()
    assert hasattr(module, "ProviderOffer")
    assert dataclasses.is_dataclass(module.ProviderOffer)

    field_names = {field.name for field in dataclasses.fields(module.ProviderOffer)}
    assert field_names == {
        "id",
        "gpu_name",
        "gpu_ram_gb",
        "reliability",
        "dph",
        "inet_up_mbps",
        "inet_down_mbps",
        "interruptible",
    }


def test_provider_offer_value_types():
    module = _load_interface_module()
    offer = module.ProviderOffer(
        id="offer-1",
        gpu_name="A100",
        gpu_ram_gb=80,
        reliability=0.99,
        dph=1.25,
        inet_up_mbps=500.0,
        inet_down_mbps=700.0,
        interruptible=False,
    )

    assert isinstance(offer.gpu_ram_gb, int)
    assert isinstance(offer.dph, float)
    assert isinstance(offer.reliability, float)
    assert isinstance(offer.inet_up_mbps, float)
    assert isinstance(offer.inet_down_mbps, float)
    assert isinstance(offer.interruptible, bool)


def test_provider_instance_dataclass_exists():
    module = _load_interface_module()
    assert hasattr(module, "ProviderInstance")
    assert dataclasses.is_dataclass(module.ProviderInstance)


def test_provider_is_abstract_with_required_methods():
    module = _load_interface_module()
    assert hasattr(module, "Provider")
    provider_cls = module.Provider
    assert inspect.isabstract(provider_cls)
    assert hasattr(provider_cls, "search_offers")
    assert hasattr(provider_cls, "create_instance")
