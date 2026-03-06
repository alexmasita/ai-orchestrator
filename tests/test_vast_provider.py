import dataclasses
import importlib
import socket
from types import SimpleNamespace

import pytest

from ai_orchestrator.provider.interface import Provider, ProviderInstance, ProviderOffer


VAST_MODULE = "ai_orchestrator.provider.vast"


def _load_vast_module():
    return importlib.import_module(VAST_MODULE)


def _base_requirements():
    return {"required_vram_gb": 24}


class _FakeResponse:
    def __init__(self, status_code, payload, *, text="", json_raises=False):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self._json_raises = json_raises

    def json(self):
        if self._json_raises:
            raise ValueError("invalid json")
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
        "search_response": _FakeResponse(200, {"offers": []}),
        "legacy_create_response": _FakeResponse(
            201,
            {"instance_id": "i-legacy", "gpu_name": "A100", "dph": 1.2},
        ),
        "ask_create_response": _FakeResponse(200, {"new_contract": "i-123"}),
        "instance_get_response": _FakeResponse(
            200,
            {"instances": {"gpu_name": "A100", "dph_total": 1.2, "public_ipaddr": "1.2.3.4"}},
        ),
        "instance_get_responses": [],
        "delete_response": _FakeResponse(200, {}),
    }

    def _get(url, headers=None, params=None, json=None):
        calls.append(("GET", url, headers, params, json))
        if "/instances/" in url:
            if state["instance_get_responses"]:
                return state["instance_get_responses"].pop(0)
            return state["instance_get_response"]
        return _FakeResponse(404, {})

    def _post(url, headers=None, params=None, json=None):
        calls.append(("POST", url, headers, params, json))
        if url.endswith("/bundles"):
            return state["search_response"]
        if url.endswith("/instances"):
            return state["legacy_create_response"]
        return _FakeResponse(404, {})

    def _put(url, headers=None, params=None, json=None):
        calls.append(("PUT", url, headers, params, json))
        return state["ask_create_response"]

    def _delete(url, headers=None):
        calls.append(("DELETE", url, headers, None, None))
        return state["delete_response"]

    fake_requests = SimpleNamespace(get=_get, post=_post, put=_put, delete=_delete)
    monkeypatch.setattr(vast, "requests", fake_requests, raising=False)
    return vast, calls, state


def test_vast_provider_exists_and_subclasses_provider():
    vast = _load_vast_module()
    assert hasattr(vast, "VastProvider")
    assert issubclass(vast.VastProvider, Provider)


def test_search_offers_posts_bundles_with_translated_json_payload(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    requirements = _base_requirements()
    provider.search_offers(requirements=requirements)

    method, url, headers, params, payload = calls[0]
    assert method == "POST"
    assert url.endswith("/bundles")
    assert headers["Authorization"] == "Bearer k-test"
    assert headers["Content-Type"] == "application/json"
    assert params is None
    assert payload == {
        "gpu_ram": {"gte": 24576},
        "rented": {"eq": False},
        "order": [["dph_total", "asc"], ["reliability", "desc"]],
    }


def test_search_offers_unknown_scalar_key_raises_with_deterministic_message(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError, match="Unsupported requirements keys: foo"):
        provider.search_offers(requirements={"required_vram_gb": 24, "foo": 1})


def test_search_offers_translates_generic_requirements_to_vast_payload(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    provider.search_offers(
        requirements={
            "required_vram_gb": 24,
            "max_dph": 2.0,
            "min_reliability": 0.98,
            "min_inet_up_mbps": 100,
            "min_inet_down_mbps": 120,
            "verified_only": True,
            "require_rentable": True,
            "allow_interruptible": True,
            "min_duration_seconds": 1800,
            "limit": 5,
        }
    )

    _method, _url, _headers, _params, payload = calls[0]
    assert payload == {
        "gpu_ram": {"gte": 24576},
        "dph_total": {"lte": 2.0},
        "reliability": {"gte": 0.98},
        "inet_up": {"gte": 100.0},
        "inet_down": {"gte": 120.0},
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "duration": {"gte": 1800},
        "type": "bid",
        "order": [["dph_total", "asc"], ["reliability", "desc"]],
        "limit": 5,
    }


def test_search_offers_interruptible_false_maps_to_ondemand(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    provider.search_offers(requirements={"required_vram_gb": 24, "allow_interruptible": False})
    _method, _url, _headers, _params, payload = calls[0]
    assert payload["type"] == "ondemand"


def test_search_offers_unknown_generic_key_raises(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError, match="Unsupported requirements keys: random_filter"):
        provider.search_offers(requirements={"required_vram_gb": 24, "random_filter": 1})


@pytest.mark.parametrize("invalid_required_vram", [None, "abc", 24.5, True])
def test_search_offers_invalid_required_vram_type_raises(_vast_and_calls, invalid_required_vram):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError, match="required_vram_gb"):
        provider.search_offers(requirements={"required_vram_gb": invalid_required_vram})


def test_search_offers_missing_required_vram_raises(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError, match="required_vram_gb is required"):
        provider.search_offers(requirements={"max_dph": 2.0})


def test_search_offers_invalid_limit_raises(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError, match="limit must be a positive int"):
        provider.search_offers(requirements={"required_vram_gb": 24, "limit": 0})


def test_search_offers_builds_bundles_endpoint_without_double_slashes(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"offers": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api/v0/")

    provider.search_offers(requirements=_base_requirements())

    method, url, _headers, _params, _payload = calls[0]
    assert method == "POST"
    assert url == "https://vast.example/api/v0/bundles"


def test_search_offers_maps_wrapped_vast_fields_to_provider_offer_fields(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "1001",
                    "ask_contract_id": "9001",
                    "gpu_name": "RTX_4090",
                    "gpu_ram": 24,
                    "reliability2": 0.98,
                    "dph_total": 1.10,
                    "inet_up": 200.0,
                    "inet_down": 400.0,
                    "is_bid": False,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    offers = provider.search_offers(requirements=_base_requirements())

    offer = offers[0]
    assert isinstance(offer, ProviderOffer)
    assert offer.id == "1001"
    assert offer.gpu_name == "RTX_4090"
    assert offer.gpu_ram_gb == 24
    assert offer.reliability == 0.98
    assert offer.dph == 1.10
    assert offer.inet_up_mbps == 200.0
    assert offer.inet_down_mbps == 400.0
    assert offer.interruptible is False


def test_search_offers_prefers_id_over_ask_contract_id_when_both_present(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "30795982",
                    "ask_contract_id": "99999999",
                    "gpu_name": "RTX_4090",
                    "gpu_ram": 24,
                    "reliability2": 0.98,
                    "dph_total": 1.10,
                    "inet_up": 200.0,
                    "inet_down": 400.0,
                    "is_bid": False,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    offers = provider.search_offers(requirements=_base_requirements())
    assert offers[0].id == "30795982"


def test_search_offers_missing_id_raises_schema_mismatch(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "ask_contract_id": "30795982",
                    "gpu_name": "RTX_4090",
                    "gpu_ram": 24,
                    "reliability2": 0.98,
                    "dph_total": 1.10,
                    "inet_up": 200.0,
                    "inet_down": 400.0,
                    "is_bid": False,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    with pytest.raises(vast.VastProviderError, match="missing or invalid id"):
        provider.search_offers(requirements=_base_requirements())


@pytest.mark.parametrize("invalid_id", [None, "", "abc", True, 12.5])
def test_search_offers_invalid_id_types_raise_schema_mismatch(_vast_and_calls, invalid_id):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": invalid_id,
                    "gpu_name": "RTX_4090",
                    "gpu_ram": 24,
                    "reliability2": 0.98,
                    "dph_total": 1.10,
                    "inet_up": 200.0,
                    "inet_down": 400.0,
                    "is_bid": False,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    with pytest.raises(vast.VastProviderError, match="missing or invalid id"):
        provider.search_offers(requirements=_base_requirements())


def test_search_offers_accepts_legacy_list_payload(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        [
            {
                "id": "101",
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
    offers = provider.search_offers(requirements=_base_requirements())
    assert [offer.id for offer in offers] == ["101"]


def test_search_offers_accepts_wrapped_single_offer_object(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": {
                "id": "102",
                "gpu_name": "A100",
                "gpu_ram": 80,
                "reliability2": 0.99,
                "dph_total": 1.2,
                "inet_up": 500.0,
                "inet_down": 600.0,
                "interruptible": False,
            }
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    offers = provider.search_offers(requirements=_base_requirements())
    assert [offer.id for offer in offers] == ["102"]


def test_search_offers_invalid_payload_shape_raises_vast_provider_error(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(200, {"unexpected": []})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    with pytest.raises(vast.VastProviderError, match="Unexpected /bundles response shape"):
        provider.search_offers(requirements=_base_requirements())


def test_search_offers_malformed_offer_raises_vast_provider_error(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "offer-1",
                    "gpu_ram": 24,
                    "dph_total": 1.0,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    with pytest.raises(vast.VastProviderError, match="Malformed offer object from Vast API"):
        provider.search_offers(requirements=_base_requirements())


def test_search_offers_preserves_api_order_exactly(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "3",
                    "gpu_name": "C",
                    "gpu_ram": 8,
                    "reliability2": 0.9,
                    "dph_total": 3.0,
                    "inet_up": 1.0,
                    "inet_down": 1.0,
                    "interruptible": True,
                },
                {
                    "id": "1",
                    "gpu_name": "A",
                    "gpu_ram": 8,
                    "reliability2": 0.9,
                    "dph_total": 1.0,
                    "inet_up": 1.0,
                    "inet_down": 1.0,
                    "interruptible": True,
                },
                {
                    "id": "2",
                    "gpu_name": "B",
                    "gpu_ram": 8,
                    "reliability2": 0.9,
                    "dph_total": 2.0,
                    "inet_up": 1.0,
                    "inet_down": 1.0,
                    "interruptible": True,
                },
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    offers = provider.search_offers(requirements=_base_requirements())
    assert [offer.id for offer in offers] == ["3", "1", "2"]


def test_search_offers_identical_input_produces_identical_output(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "501",
                    "gpu_name": "A100",
                    "gpu_ram": 80,
                    "reliability2": 0.99,
                    "dph_total": 1.2,
                    "inet_up": 500.0,
                    "inet_down": 600.0,
                    "interruptible": False,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    first = provider.search_offers(requirements=_base_requirements())
    second = provider.search_offers(requirements=_base_requirements())
    assert first == second


def test_search_offers_returns_copy_not_same_list_object(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "601",
                    "gpu_name": "A100",
                    "gpu_ram": 80,
                    "reliability2": 0.99,
                    "dph_total": 1.2,
                    "inet_up": 500.0,
                    "inet_down": 600.0,
                    "interruptible": False,
                }
            ]
        },
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    first = provider.search_offers(requirements=_base_requirements())
    second = provider.search_offers(requirements=_base_requirements())
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


def test_create_instance_posts_instances_with_offer_and_snapshot_and_maps_response(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["legacy_create_response"] = _FakeResponse(
        201,
        {"instance_id": "i-123", "gpu_name": "A100", "dph": 1.2},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(offer_id="offer-1", snapshot_version="snap-v1")

    method, url, headers, _params, payload = calls[0]
    assert method == "POST"
    assert url.endswith("/instances")
    assert headers["Authorization"] == "Bearer k-test"
    assert payload["offer_id"] == "offer-1"
    assert payload["snapshot_version"] == "snap-v1"
    assert isinstance(instance, ProviderInstance)
    assert instance.instance_id == "i-123"
    assert instance.gpu_name == "A100"
    assert instance.dph == 1.2


def test_create_instance_puts_asks_and_fetches_instance_metadata(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-900"})
    state["instance_get_response"] = _FakeResponse(
        200,
        {"instances": {"gpu_name": "RTX_4090", "dph_total": 0.72, "public_ipaddr": "1.2.3.4"}},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(
        offer_id="offer-1",
        snapshot_version="snap-v1",
        instance_config={"bootstrap_script": "echo boot"},
    )

    assert calls[0][0] == "PUT"
    assert calls[0][1].endswith("/asks/offer-1")
    assert calls[1][0] == "GET"
    assert calls[1][1].endswith("/instances/i-900")
    assert instance.instance_id == "i-900"
    assert instance.gpu_name == "RTX_4090"
    assert instance.dph == 0.72
    assert instance.public_ip == "1.2.3.4"


def test_create_instance_polls_until_ip_and_running(monkeypatch, _vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-901"})
    state["instance_get_responses"] = [
        _FakeResponse(
            200,
            {"instances": {"gpu_name": "RTX_4090", "dph_total": 0.72, "actual_status": "loading"}},
        ),
        _FakeResponse(
            200,
            {
                "instances": {
                    "gpu_name": "RTX_4090",
                    "dph_total": 0.72,
                    "public_ipaddr": "1.2.3.4",
                    "actual_status": "running",
                }
            },
        ),
    ]
    sleep_calls = []
    monkeypatch.setattr(vast.time, "sleep", lambda seconds: sleep_calls.append(seconds))
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(
        offer_id="offer-1",
        snapshot_version="snap-v1",
        instance_config={"bootstrap_script": "echo boot"},
    )

    get_calls = [call for call in calls if call[0] == "GET"]
    assert len(get_calls) == 2
    assert sleep_calls == [2]
    assert instance.public_ip == "1.2.3.4"


def test_create_instance_status_gate_waits_for_running(monkeypatch, _vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-902"})
    state["instance_get_responses"] = [
        _FakeResponse(
            200,
            {
                "instances": {
                    "gpu_name": "RTX_4090",
                    "dph_total": 0.72,
                    "public_ipaddr": "1.2.3.4",
                    "actual_status": "loading",
                }
            },
        ),
        _FakeResponse(
            200,
            {
                "instances": {
                    "gpu_name": "RTX_4090",
                    "dph_total": 0.72,
                    "public_ipaddr": "1.2.3.4",
                    "actual_status": "running",
                }
            },
        ),
    ]
    sleep_calls = []
    monkeypatch.setattr(vast.time, "sleep", lambda seconds: sleep_calls.append(seconds))
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(
        offer_id="offer-1",
        snapshot_version="snap-v1",
        instance_config={"bootstrap_script": "echo boot"},
    )

    get_calls = [call for call in calls if call[0] == "GET"]
    assert len(get_calls) == 2
    assert sleep_calls == [2]
    assert instance.public_ip == "1.2.3.4"


def test_create_instance_timeout_raises_vast_provider_error(monkeypatch, _vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "1001",
                    "gpu_name": "RTX_4090",
                    "gpu_ram": 24,
                    "reliability2": 0.98,
                    "dph_total": 0.72,
                    "inet_up": 200.0,
                    "inet_down": 400.0,
                    "is_bid": False,
                }
            ]
        },
    )
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-903"})
    state["instance_get_response"] = _FakeResponse(
        200,
        {"instances": {"gpu_name": "RTX_4090", "dph_total": 0.72, "actual_status": "loading"}},
    )
    clock = {"now": 0.0}
    sleep_calls = []

    def _monotonic():
        return clock["now"]

    def _sleep(seconds):
        sleep_calls.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(vast.time, "monotonic", _monotonic)
    monkeypatch.setattr(vast.time, "sleep", _sleep)
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    provider.search_offers(
        requirements={
            "required_vram_gb": 24,
            "instance_ready_timeout_seconds": 6,
        }
    )

    with pytest.raises(vast.VastProviderError, match="instance did not reach running\\+ip state"):
        provider.create_instance(
            offer_id="1001",
            snapshot_version="snap-v1",
            instance_config={"bootstrap_script": "echo boot"},
        )

    assert sleep_calls == [2, 2, 2]
    get_calls = [call for call in calls if call[0] == "GET"]
    assert len(get_calls) == 4


def test_create_instance_immediate_ready_skips_sleep(monkeypatch, _vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-904"})
    state["instance_get_response"] = _FakeResponse(
        200,
        {
            "instances": {
                "gpu_name": "RTX_4090",
                "dph_total": 0.72,
                "public_ipaddr": "1.2.3.4",
                "actual_status": "running",
            }
        },
    )
    sleep_calls = []
    monkeypatch.setattr(vast.time, "sleep", lambda seconds: sleep_calls.append(seconds))
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(
        offer_id="offer-1",
        snapshot_version="snap-v1",
        instance_config={"bootstrap_script": "echo boot"},
    )

    assert instance.public_ip == "1.2.3.4"
    assert sleep_calls == []
    get_calls = [call for call in calls if call[0] == "GET"]
    assert len(get_calls) == 1


@pytest.mark.parametrize(
    ("instance_payload", "expected_ip"),
    [
        ({"gpu_name": "RTX_4090", "dph_total": 0.72, "public_ipaddr": "1.2.3.4"}, "1.2.3.4"),
        ({"gpu_name": "RTX_4090", "dph_total": 0.72, "public_ip": "5.6.7.8"}, "5.6.7.8"),
    ],
)
def test_create_instance_accepts_public_ip_variants(_vast_and_calls, instance_payload, expected_ip):
    vast, _, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-905"})
    state["instance_get_response"] = _FakeResponse(200, {"instances": instance_payload})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    instance = provider.create_instance(
        offer_id="offer-1",
        snapshot_version="snap-v1",
        instance_config={"bootstrap_script": "echo boot"},
    )

    assert instance.public_ip == expected_ip


def test_create_instance_timeout_override_is_applied(monkeypatch, _vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        200,
        {
            "offers": [
                {
                    "id": "1001",
                    "gpu_name": "RTX_4090",
                    "gpu_ram": 24,
                    "reliability2": 0.98,
                    "dph_total": 0.72,
                    "inet_up": 200.0,
                    "inet_down": 400.0,
                    "is_bid": False,
                }
            ]
        },
    )
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-906"})
    state["instance_get_response"] = _FakeResponse(
        200,
        {"instances": {"gpu_name": "RTX_4090", "dph_total": 0.72}},
    )
    clock = {"now": 0.0}
    sleep_calls = []

    def _monotonic():
        return clock["now"]

    def _sleep(seconds):
        sleep_calls.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(vast.time, "monotonic", _monotonic)
    monkeypatch.setattr(vast.time, "sleep", _sleep)
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")
    provider.search_offers(
        requirements={
            "required_vram_gb": 24,
            "instance_ready_timeout_seconds": 6,
        }
    )

    with pytest.raises(
        vast.VastProviderError,
        match="instance did not reach running\\+ip state within 6s",
    ):
        provider.create_instance(
            offer_id="1001",
            snapshot_version="snap-v1",
            instance_config={"bootstrap_script": "echo boot"},
        )

    assert sleep_calls == [2, 2, 2]
    get_calls = [call for call in calls if call[0] == "GET"]
    assert len(get_calls) == 4


def test_create_instance_missing_new_contract_raises_vast_provider_error(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"success": True})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError, match="missing new_contract"):
        provider.create_instance(
            offer_id="offer-1",
            snapshot_version="snap-v1",
            instance_config={"bootstrap_script": "echo boot"},
        )

    assert len(calls) == 1
    assert calls[0][0] == "PUT"


def test_destroy_instance_deletes_instances_id(_vast_and_calls):
    vast, calls, state = _vast_and_calls
    state["delete_response"] = _FakeResponse(200, {})
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    provider.destroy_instance("i-123")

    method, url, headers, _params, _payload = calls[0]
    assert method == "DELETE"
    assert url.endswith("/instances/i-123")
    assert headers["Authorization"] == "Bearer k-test"


@pytest.mark.parametrize(
    ("method_name", "state_key", "status_code", "call_kwargs"),
    [
        ("search_offers", "search_response", 500, {"requirements": {"required_vram_gb": 24}}),
        (
            "create_instance",
            "legacy_create_response",
            500,
            {"offer_id": "offer-1", "snapshot_version": "snap-v1"},
        ),
        (
            "create_instance",
            "ask_create_response",
            500,
            {
                "offer_id": "offer-1",
                "snapshot_version": "snap-v1",
                "instance_config": {"bootstrap_script": "echo boot"},
            },
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
        ("search_offers", {"requirements": {"required_vram_gb": 24}}),
        ("create_instance", {"offer_id": "offer-1", "snapshot_version": "snap-v1"}),
        (
            "create_instance",
            {
                "offer_id": "offer-1",
                "snapshot_version": "snap-v1",
                "instance_config": {"bootstrap_script": "echo boot"},
            },
        ),
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


def test_bundles_error_surfaces_api_message_and_no_secret_leak(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        400,
        {"msg": "Invalid json body", "error": "invalid_request"},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError) as exc_info:
        provider.search_offers(requirements={"required_vram_gb": 24})

    message = str(exc_info.value)
    assert message == "Vast /bundles failed: status=400 msg=Invalid json body invalid_request"
    assert "k-test" not in message
    assert "Authorization" not in message


def test_asks_error_surfaces_api_message_and_no_secret_leak(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(
        400,
        {"msg": "no_such_ask", "error": "invalid_args"},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError) as exc_info:
        provider.create_instance(
            offer_id="offer-1",
            snapshot_version="snap-v1",
            instance_config={"bootstrap_script": "echo boot"},
        )

    message = str(exc_info.value)
    assert message == "Vast /asks failed: status=400 msg=no_such_ask invalid_args"
    assert "k-test" not in message
    assert "Authorization" not in message


def test_instances_error_surfaces_api_message_for_followup_get(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["ask_create_response"] = _FakeResponse(200, {"new_contract": "i-900"})
    state["instance_get_response"] = _FakeResponse(
        500,
        {"msg": "backend unavailable", "error": "temporary_error"},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError) as exc_info:
        provider.create_instance(
            offer_id="offer-1",
            snapshot_version="snap-v1",
            instance_config={"bootstrap_script": "echo boot"},
        )

    message = str(exc_info.value)
    assert message == "Vast /instances failed: status=500 msg=backend unavailable temporary_error"
    assert "k-test" not in message
    assert "Authorization" not in message


def test_non_json_error_response_uses_first_200_chars_of_text(_vast_and_calls):
    vast, _, state = _vast_and_calls
    body = "x" * 260
    state["ask_create_response"] = _FakeResponse(400, {}, text=body, json_raises=True)
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError) as exc_info:
        provider.create_instance(
            offer_id="offer-1",
            snapshot_version="snap-v1",
            instance_config={"bootstrap_script": "echo boot"},
        )

    message = str(exc_info.value)
    assert message == f"Vast /asks failed: status=400 msg={body[:200]}"


def test_error_formatting_is_deterministic_for_identical_failures(_vast_and_calls):
    vast, _, state = _vast_and_calls
    state["search_response"] = _FakeResponse(
        400,
        {"msg": "Invalid json body", "error": "invalid_request"},
    )
    provider = vast.VastProvider(api_key="k-test", base_url="https://vast.example/api")

    with pytest.raises(vast.VastProviderError) as first_exc:
        provider.search_offers(requirements={"required_vram_gb": 24})
    with pytest.raises(vast.VastProviderError) as second_exc:
        provider.search_offers(requirements={"required_vram_gb": 24})

    assert str(first_exc.value) == str(second_exc.value)
