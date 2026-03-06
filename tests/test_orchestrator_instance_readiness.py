import importlib

import pytest


ORCHESTRATOR_MODULE = "ai_orchestrator.orchestrator"
HEALTHCHECK_MODULE = "ai_orchestrator.runtime.healthcheck"
INTERFACE_MODULE = "ai_orchestrator.provider.interface"


def _load_orchestrator_module():
    return importlib.import_module(ORCHESTRATOR_MODULE)


def _load_healthcheck_module():
    return importlib.import_module(HEALTHCHECK_MODULE)


def _load_interface_module():
    return importlib.import_module(INTERFACE_MODULE)


def _sample_config():
    return {
        "snapshot_version": "snap-v1",
        "idle_timeout_seconds": 1800,
        "min_reliability": 0.90,
        "min_inet_up_mbps": 100.0,
        "min_inet_down_mbps": 100.0,
        "allow_interruptible": True,
        "max_dph": 2.00,
    }


def _sample_models():
    return ["deepseek_llamacpp", "whisper"]


def _sample_offer():
    interface = _load_interface_module()
    return interface.ProviderOffer(
        id="offer-1",
        gpu_name="RTX_4090",
        gpu_ram_gb=24,
        reliability=0.99,
        dph=0.5,
        inet_up_mbps=100.0,
        inet_down_mbps=100.0,
        interruptible=False,
    )


class _RecordingProvider:
    def __init__(self):
        self.create_calls = []

    def search_offers(self, _requirements):
        return []

    def create_instance(self, offer_id, snapshot_version, instance_config):
        interface = _load_interface_module()
        self.create_calls.append((offer_id, snapshot_version, instance_config))
        instance = interface.ProviderInstance(
            instance_id="abc123",
            gpu_name="RTX_4090",
            dph=0.5,
        )
        instance.public_ip = "1.2.3.4"
        return instance


def _monkeypatch_common(monkeypatch, orch, readiness_stub):
    healthcheck = _load_healthcheck_module()
    monkeypatch.setattr(orch, "select_offer", lambda *args, **kwargs: _sample_offer(), raising=False)
    monkeypatch.setattr(
        orch,
        "generate_bootstrap_script",
        lambda _config, _models: "#!/usr/bin/env bash\nset -e\necho boot",
        raising=False,
    )
    monkeypatch.setattr(orch, "wait_for_instance_ready", readiness_stub, raising=False)
    monkeypatch.setattr(healthcheck, "wait_for_instance_ready", readiness_stub, raising=True)


def _extract_url(args, kwargs, kw_key, arg_pos):
    value = kwargs.get(kw_key)
    if value is not None:
        return value
    if len(args) > arg_pos:
        return args[arg_pos]
    return None


def test_wait_for_instance_ready_import_contract_callable():
    module = _load_healthcheck_module()
    assert hasattr(module, "wait_for_instance_ready")
    assert callable(module.wait_for_instance_ready)


def test_run_orchestration_calls_wait_for_instance_ready_once(monkeypatch):
    orch = _load_orchestrator_module()
    calls = []
    provider = _RecordingProvider()

    def _ready(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)
    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(calls) == 1


def test_run_orchestration_calls_wait_for_instance_ready_with_expected_urls(monkeypatch):
    orch = _load_orchestrator_module()
    calls = []
    provider = _RecordingProvider()

    def _ready(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)
    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(calls) == 1
    args, kwargs = calls[0]
    deepseek_url = _extract_url(args, kwargs, "deepseek_url", 3)
    whisper_url = _extract_url(args, kwargs, "whisper_url", 4)
    assert deepseek_url == "http://1.2.3.4:8080"
    assert whisper_url == "http://1.2.3.4:9000"


def test_run_orchestration_propagates_wait_for_instance_ready_failure(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()

    def _ready_fail(*_args, **_kwargs):
        raise RuntimeError("instance not ready")

    _monkeypatch_common(monkeypatch, orch, _ready_fail)

    with pytest.raises(RuntimeError):
        orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(provider.create_calls) == 1


def test_run_orchestration_readiness_call_sequence_is_deterministic(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    call_sequence = []

    def _ready(*args, **kwargs):
        call_sequence.append((args, tuple(sorted(kwargs.items()))))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)

    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())
    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(call_sequence) == 2
    assert call_sequence[0] == call_sequence[1]


def test_run_orchestration_output_contains_readiness_urls(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    calls = []

    def _ready(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)
    result = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(calls) == 1
    args, kwargs = calls[0]
    deepseek_url = _extract_url(args, kwargs, "deepseek_url", 3)
    whisper_url = _extract_url(args, kwargs, "whisper_url", 4)

    assert "deepseek_url" in result
    assert "whisper_url" in result
    assert result["deepseek_url"] == deepseek_url
    assert result["whisper_url"] == whisper_url
    assert result["deepseek_url"] == "http://1.2.3.4:8080"
    assert result["whisper_url"] == "http://1.2.3.4:9000"


def test_run_orchestration_calls_create_then_readiness(monkeypatch):
    orch = _load_orchestrator_module()
    events = []

    class _OrderedProvider(_RecordingProvider):
        def create_instance(self, offer_id, snapshot_version, instance_config):
            events.append("create_instance")
            return super().create_instance(offer_id, snapshot_version, instance_config)

    provider = _OrderedProvider()

    def _ready(*_args, **_kwargs):
        events.append("wait_for_instance_ready")
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)
    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert events == ["create_instance", "wait_for_instance_ready"]


def test_run_orchestration_uses_provider_public_ip_for_readiness_urls(monkeypatch):
    orch = _load_orchestrator_module()
    calls = []

    class _PublicIpProvider(_RecordingProvider):
        def create_instance(self, offer_id, snapshot_version, instance_config):
            interface = _load_interface_module()
            self.create_calls.append((offer_id, snapshot_version, instance_config))
            instance = interface.ProviderInstance(
                instance_id="abc123",
                gpu_name="RTX_4090",
                dph=0.5,
            )
            instance.public_ip = "9.8.7.6"
            return instance

    provider = _PublicIpProvider()

    def _ready(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)
    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(calls) == 1
    args, kwargs = calls[0]
    deepseek_url = _extract_url(args, kwargs, "deepseek_url", 3)
    whisper_url = _extract_url(args, kwargs, "whisper_url", 4)
    assert deepseek_url == "http://9.8.7.6:8080"
    assert whisper_url == "http://9.8.7.6:9000"


def test_run_orchestration_readiness_url_args_are_deterministic(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    call_urls = []

    def _ready(*args, **kwargs):
        deepseek_url = _extract_url(args, kwargs, "deepseek_url", 3)
        whisper_url = _extract_url(args, kwargs, "whisper_url", 4)
        call_urls.append((deepseek_url, whisper_url))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)

    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())
    _ = orch.run_orchestration(provider, _sample_config(), _sample_models())

    assert len(call_urls) == 2
    assert call_urls[0] == call_urls[1]


def test_run_orchestration_propagates_readiness_timeout_from_config(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    calls = []
    config = _sample_config()
    config["instance_ready_timeout_seconds"] = 1200

    def _ready(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    _monkeypatch_common(monkeypatch, orch, _ready)
    _ = orch.run_orchestration(provider, config, _sample_models())

    assert len(calls) == 1
    _args, kwargs = calls[0]
    assert kwargs["timeout"] == 1200
