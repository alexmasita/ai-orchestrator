import importlib

import pytest


ORCHESTRATOR_MODULE = "ai_orchestrator.orchestrator"
INTERFACE_MODULE = "ai_orchestrator.provider.interface"


def _load_orchestrator_module():
    return importlib.import_module(ORCHESTRATOR_MODULE)


def _load_interface_module():
    return importlib.import_module(INTERFACE_MODULE)


def _sample_config():
    return {
        "snapshot_version": "snap-v1",
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
    def __init__(self, events):
        self._events = events
        self.create_calls = []
        self.search_calls = []

    def search_offers(self, requirements):
        self.search_calls.append(requirements)
        return []

    def create_instance(self, offer_id, snapshot_version, instance_config):
        interface = _load_interface_module()
        self._events.append("create_instance")
        self.create_calls.append(
            {
                "offer_id": offer_id,
                "snapshot_version": snapshot_version,
                "instance_config": instance_config,
            }
        )
        return interface.ProviderInstance(
            instance_id=f"mock-{offer_id}",
            gpu_name="RTX_4090",
            dph=0.5,
        )


def test_run_orchestration_exists_and_callable():
    module = _load_orchestrator_module()
    assert hasattr(module, "run_orchestration")
    assert callable(module.run_orchestration)


def test_run_orchestration_calls_generator_and_injects_script(monkeypatch):
    orch = _load_orchestrator_module()
    config = _sample_config()
    models = _sample_models()
    script = "#!/usr/bin/env bash\nset -e\necho boot"

    events = []
    generator_calls = []

    def _fake_generate_bootstrap_script(cfg, mdl):
        events.append("generate_bootstrap_script")
        generator_calls.append((cfg, mdl))
        return script

    monkeypatch.setattr(
        orch,
        "generate_bootstrap_script",
        _fake_generate_bootstrap_script,
        raising=False,
    )
    monkeypatch.setattr(
        orch,
        "select_offer",
        lambda *args, **kwargs: _sample_offer(),
        raising=False,
    )

    provider = _RecordingProvider(events)
    _ = orch.run_orchestration(provider, config, models)

    assert len(generator_calls) == 1
    assert generator_calls[0] == (config, models)

    assert len(provider.create_calls) == 1
    create_call = provider.create_calls[0]
    assert create_call["offer_id"] == "offer-1"
    assert create_call["snapshot_version"] == config["snapshot_version"]
    assert create_call["instance_config"] == {"bootstrap_script": script}
    assert create_call["instance_config"]["bootstrap_script"] == script
    assert isinstance(script, str)
    assert script != ""
    assert script == script.strip()

    assert events == ["generate_bootstrap_script", "create_instance"]


@pytest.mark.parametrize("bad_script", ["", None, 123])
def test_run_orchestration_rejects_invalid_bootstrap_script(monkeypatch, bad_script):
    orch = _load_orchestrator_module()
    config = _sample_config()
    models = _sample_models()
    events = []
    provider = _RecordingProvider(events)

    monkeypatch.setattr(
        orch,
        "generate_bootstrap_script",
        lambda _cfg, _mdl: bad_script,
        raising=False,
    )
    monkeypatch.setattr(
        orch,
        "select_offer",
        lambda *args, **kwargs: _sample_offer(),
        raising=False,
    )

    with pytest.raises(ValueError):
        orch.run_orchestration(provider, config, models)

    assert provider.create_calls == []


def test_run_orchestration_propagates_generator_runtime_error(monkeypatch):
    orch = _load_orchestrator_module()
    config = _sample_config()
    models = _sample_models()
    events = []
    provider = _RecordingProvider(events)

    def _raise_runtime_error(_cfg, _mdl):
        raise RuntimeError("boom")

    monkeypatch.setattr(orch, "generate_bootstrap_script", _raise_runtime_error, raising=False)
    monkeypatch.setattr(
        orch,
        "select_offer",
        lambda *args, **kwargs: _sample_offer(),
        raising=False,
    )

    with pytest.raises(RuntimeError):
        orch.run_orchestration(provider, config, models)

    assert provider.create_calls == []


def test_run_orchestration_determinism_and_instance_config_isolation(monkeypatch):
    orch = _load_orchestrator_module()
    config = _sample_config()
    models = _sample_models()
    script = "#!/usr/bin/env bash\nset -e\necho boot"

    events = []
    generator_calls = []
    provider = _RecordingProvider(events)

    def _fake_generate_bootstrap_script(cfg, mdl):
        events.append("generate_bootstrap_script")
        generator_calls.append((cfg, mdl))
        return script

    monkeypatch.setattr(
        orch,
        "generate_bootstrap_script",
        _fake_generate_bootstrap_script,
        raising=False,
    )
    monkeypatch.setattr(
        orch,
        "select_offer",
        lambda *args, **kwargs: _sample_offer(),
        raising=False,
    )

    first = orch.run_orchestration(provider, config, models)
    second = orch.run_orchestration(provider, config, models)

    assert first == second
    assert len(generator_calls) == 2
    assert generator_calls[0] == (config, models)
    assert generator_calls[1] == (config, models)

    assert len(provider.create_calls) == 2
    first_cfg = provider.create_calls[0]["instance_config"]
    second_cfg = provider.create_calls[1]["instance_config"]
    assert first_cfg["bootstrap_script"] == script
    assert second_cfg["bootstrap_script"] == script
    assert id(first_cfg) != id(second_cfg)

    assert events == [
        "generate_bootstrap_script",
        "create_instance",
        "generate_bootstrap_script",
        "create_instance",
    ]


def test_run_orchestration_passes_provider_agnostic_requirements_and_runtime_only_instance_config(
    monkeypatch,
):
    orch = _load_orchestrator_module()
    script = "#!/usr/bin/env bash\nset -e\necho boot"
    config = _sample_config() | {
        "idle_timeout_seconds": 1800,
        "verified_only": True,
        "limit": 5,
    }
    models = _sample_models()
    events = []

    class _SearchProvider(_RecordingProvider):
        def search_offers(self, requirements):
            self.search_calls.append(requirements)
            return [_sample_offer()]

    provider = _SearchProvider(events)
    monkeypatch.setattr(
        orch,
        "generate_bootstrap_script",
        lambda _cfg, _mdl: script,
        raising=False,
    )

    orch.run_orchestration(provider, config, models, required_vram_gb=24)

    assert len(provider.search_calls) == 1
    search_requirements = provider.search_calls[0]
    assert search_requirements == {
        "required_vram_gb": 24,
        "max_dph": 2.0,
        "min_reliability": 0.9,
        "min_inet_up_mbps": 100.0,
        "min_inet_down_mbps": 100.0,
        "verified_only": True,
        "require_rentable": True,
        "allow_interruptible": True,
        "min_duration_seconds": 1800,
        "limit": 5,
    }
    forbidden = {"dph_total", "inet_up", "inet_down", "verified", "rentable"}
    assert forbidden.isdisjoint(set(search_requirements))

    assert len(provider.create_calls) == 1
    instance_config = provider.create_calls[0]["instance_config"]
    assert instance_config == {
        "bootstrap_script": script,
        "idle_timeout_seconds": 1800,
    }
