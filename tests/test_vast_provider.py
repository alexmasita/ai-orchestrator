import dataclasses
import importlib
import socket
from types import SimpleNamespace

import pytest

from ai_orchestrator.provider.interface import Provider, ProviderInstance, ProviderOffer


VAST_MODULE = "ai_orchestrator.provider.vast"


def _load_vast_module():
    return importlib.import_module(VAST_MODULE)


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _disable_real_network(monkeypatch):
    def _deny_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in tests")

    monkeypatch.setattr(socket, "create_connection", _deny_network)


@pytest.fixture
def _vast_and_calls(monkeypatch):
    vast = _load_vast_module()
    calls = []

    state = {
        "get_response": _FakeResponse(200, []),
        "post_response": _FakeResponse(201, {}),
        "delete_response": _FakeResponse(200, {}),
    }

    def _get(url, headers=None, params=None):
        calls.append(("GET", url, headers, params))
        return state["get_response"]

    def _post(url, headers=None, json=None):
        calls.append(("POST", url, headers, json))
        return state["post_response"]

    def _delete(url, headers=None):
        calls.append(("DELETE", url, headers, None))
        return state["delete_response"]

    fake_requests = SimpleNamespace(get=_get, post=_post, delete=_delete)
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)
    return vast, calls, state


def test_vast_provider_exists_and_subclasses_provider():
    vast = _load_vast_module()
    assert hasattr(vast, "VastProvider")
    assert issubclass(vast.VastProvider, Provider)


def test_search_offers_calls_bundles_with_auth_header_and_query_params(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["get_response"] = _FakeResponse(200, [])
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    requirements = {
        "required_vram_gb": 24,
        "max_dph": 2.0,
        "min_reliability": 0.95,
    }
    provider.search_offers(requirements=requirements)

    method, url, headers, params = calls[0]
    assert method == "GET"
    assert url.endswith("/bundles")
    assert headers["Authorization"] == "Bearer k-test"
    assert params == requirements


def test_search_offers_builds_bundles_endpoint_without_double_slashes(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["get_response"] = _FakeResponse(200, [])
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0/")

    provider.search_offers(requirements={})

    method, url, _headers, _params = calls[0]
    assert method == "GET"
    assert url == "https://vast.example/api/v0/bundles"


def test_search_offers_maps_vast_fields_to_provider_offer_fields(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["get_response"] = _FakeResponse(
        200,
        [
            {
                "id": "offer-1",
                "gpu_name": "RTX_4090",
                "gpu_ram": 24,
                "reliability2": 0.98,
                "dph_total": 1.10,
                "inet_up": 200.0,
                "inet_down": 400.0,
                "interruptible": False,
            }
        ],
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    offers = provider.search_offers(requirements={})

    offer = offers[0]
    assert isinstance(offer, ProviderOffer)
    assert offer.id == "offer-1"
    assert offer.gpu_name == "RTX_4090"
    assert offer.gpu_ram_gb == 24
    assert offer.reliability == 0.98
    assert offer.dph == 1.10
    assert offer.inet_up_mbps == 200.0
    assert offer.inet_down_mbps == 400.0
    assert offer.interruptible is False


def test_search_offers_preserves_api_order_exactly(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["get_response"] = _FakeResponse(
        200,
        [
            {
                "id": "third",
                "gpu_name": "C",
                "gpu_ram": 8,
                "reliability2": 0.9,
                "dph_total": 3.0,
                "inet_up": 1.0,
                "inet_down": 1.0,
                "interruptible": True,
            },
            {
                "id": "first",
                "gpu_name": "A",
                "gpu_ram": 8,
                "reliability2": 0.9,
                "dph_total": 1.0,
                "inet_up": 1.0,
                "inet_down": 1.0,
                "interruptible": True,
            },
            {
                "id": "second",
                "gpu_name": "B",
                "gpu_ram": 8,
                "reliability2": 0.9,
                "dph_total": 2.0,
                "inet_up": 1.0,
                "inet_down": 1.0,
                "interruptible": True,
            },
        ],
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    offers = provider.search_offers(requirements={})
    assert [offer.id for offer in offers] == ["third", "first", "second"]


def test_search_offers_identical_input_produces_identical_output(_vast_and_calls):
    vast, _, state = _vast_and_calls
    payload = [
        {
            "id": "offer-1",
            "gpu_name": "A100",
            "gpu_ram": 80,
            "reliability2": 0.99,
            "dph_total": 1.2,
            "inet_up": 500.0,
            "inet_down": 600.0,
            "interruptible": False,
        }
    ]
    state["get_response"] = _FakeResponse(200, payload)
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    first = provider.search_offers(requirements={"x": 1})
    second = provider.search_offers(requirements={"x": 1})
    assert first == second


def test_search_offers_returns_copy_not_same_list_object(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["get_response"] = _FakeResponse(
        200,
        [
            {
                "id": "offer-1",
                "gpu_name": "A100",
                "gpu_ram": 80,
                "reliability2": 0.99,
                "dph_total": 1.2,
                "inet_up": 500.0,
                "inet_down": 600.0,
                "interruptible": False,
            }
        ],
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    first = provider.search_offers(requirements={})
    second = provider.search_offers(requirements={})
    assert first == second
    assert first is not second


def test_provider_offer_dataclass_equality_for_deterministic_comparisons():
    left = ProviderOffer(
        id="offer-1",
        gpu_name="A100",
        gpu_ram_gb=80,
        reliability=0.99,
        dph=1.2,
        inet_up_mbps=500.0,
        inet_down_mbps=600.0,
        interruptible=False,
    )
    equal = ProviderOffer(
        id="offer-1",
        gpu_name="A100",
        gpu_ram_gb=80,
        reliability=0.99,
        dph=1.2,
        inet_up_mbps=500.0,
        inet_down_mbps=600.0,
        interruptible=False,
    )
    different = dataclasses.replace(left, dph=1.3)
    assert left == equal
    assert left != different


def test_create_instance_posts_instances_with_offer_and_snapshot_and_maps_response(
    _vast_and_calls,
):
    vast, calls, state = _vast_and_calls
    state["post_response"] = _FakeResponse(
        201,
        {"instance_id": "i-123", "gpu_name": "A100", "dph": 1.2},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(offer_id="offer-1", snapshot_version="snap-v1")

    method, url, headers, payload = calls[0]
    assert method == "POST"
    assert url.endswith("/instances")
    assert headers["Authorization"] == "Bearer k-test"
    assert payload["offer_id"] == "offer-1"
    assert payload["snapshot_version"] == "snap-v1"
    assert isinstance(instance, ProviderInstance)
    assert instance.instance_id == "i-123"
    assert instance.gpu_name == "A100"
    assert instance.dph == 1.2


def test_destroy_instance_deletes_instances_id(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["delete_response"] = _FakeResponse(200, {})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    provider.destroy_instance("i-123")

    method, url, headers, _ = calls[0]
    assert method == "DELETE"
    assert url.endswith("/instances/i-123")
    assert headers["Authorization"] == "Bearer k-test"


@pytest.mark.parametrize(
    ("method_name", "state_key", "status_code", "call_kwargs"),
    [
        ("search_offers", "get_response", 500, {"requirements": {}}),
        (
            "create_instance",
            "post_response",
            500,
            {"offer_id": "offer-1", "snapshot_version": "snap-v1"},
        ),
        ("destroy_instance", "delete_response", 500, {"instance_id": "i-123"}),
    ],
)
def test_non_200_or_201_raises_vast_provider_error(
    _vast_and_calls, method_name, state_key, status_code, call_kwargs
):
    vast, _, state = _vast_and_calls
    state[state_key] = _FakeResponse(status_code, {})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError):
        getattr(provider, method_name)(**call_kwargs)


@pytest.mark.parametrize(
    ("method_name", "kwargs"),
    [
        ("search_offers", {"requirements": {}}),
        ("create_instance", {"offer_id": "offer-1", "snapshot_version": "snap-v1"}),
        ("create_instance", {"offer_id": "offer-1", "snapshot_version": "snap-v1", "instance_config": {"bootstrap_script": "echo boot"}}),
        ("destroy_instance", {"instance_id": "i-123"}),
    ],
)
def test_request_exceptions_are_wrapped_as_vast_provider_error(monkeypatch, method_name, kwargs):
    vast = _load_vast_module()

    class _RequestException(Exception):
        pass

    def _boom(*_args, **_kwargs):
        raise _RequestException("network down")

    fake_requests = SimpleNamespace(
        exceptions=SimpleNamespace(RequestException=_RequestException),
        get=_boom,
        post=_boom,
        put=_boom,
        delete=_boom,
    )
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0")

    with pytest.raises(vast.VastProviderError) as exc_info:
        getattr(provider, method_name)(**kwargs)
    assert "request failed" in str(exc_info.value).lower()
