import importlib

import pytest


ORCHESTRATOR_MODULE = "ai_orchestrator.orchestrator"
INTERFACE_MODULE = "ai_orchestrator.provider.interface"


def _load_orchestrator_module():
    return importlib.import_module(ORCHESTRATOR_MODULE)


def _load_interface_module():
    return importlib.import_module(INTERFACE_MODULE)


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


def _base_config():
    return {
        "snapshot_version": "v1",
        "min_reliability": 0.90,
        "min_inet_up_mbps": 100.0,
        "min_inet_down_mbps": 100.0,
        "allow_interruptible": True,
        "max_dph": 2.00,
    }


def _config_with_timeout(value):
    cfg = _base_config()
    cfg["idle_timeout_seconds"] = value
    return cfg


class _RecordingProvider:
    def __init__(self):
        self.create_calls = []

    def search_offers(self, _requirements):
        return []

    def create_instance(self, offer_id, snapshot_version, instance_config):
        interface = _load_interface_module()
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
    orch = _load_orchestrator_module()
    assert hasattr(orch, "run_orchestration")
    assert callable(orch.run_orchestration)


def test_idle_timeout_seconds_is_propagated_to_provider_instance_config(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    script = "#!/usr/bin/env bash\nset -e\necho boot"

    monkeypatch.setattr(orch, "select_offer", lambda *args, **kwargs: _sample_offer(), raising=False)
    monkeypatch.setattr(
        orch,
        "_resolve_bootstrap_script",
        lambda _config: script,
        raising=False,
    )

    orch.run_orchestration(provider, _config_with_timeout(1800), _sample_models())

    assert len(provider.create_calls) == 1
    instance_config = provider.create_calls[0]["instance_config"]
    assert instance_config["idle_timeout_seconds"] == 1800


@pytest.mark.parametrize("bad_timeout", [0, -1, "string", None, 1800.5])
def test_invalid_idle_timeout_raises_value_error_before_resolver_and_provider(monkeypatch, bad_timeout):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    resolver_calls = []

    def _resolver(_config):
        resolver_calls.append(True)
        return "#!/usr/bin/env bash\nset -e\necho boot"

    monkeypatch.setattr(orch, "select_offer", lambda *args, **kwargs: _sample_offer(), raising=False)
    monkeypatch.setattr(orch, "_resolve_bootstrap_script", _resolver, raising=False)

    with pytest.raises(ValueError):
        orch.run_orchestration(provider, _config_with_timeout(bad_timeout), _sample_models())

    assert resolver_calls == []
    assert provider.create_calls == []


def test_timeout_absence_keeps_instance_config_compatible(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()

    monkeypatch.setattr(orch, "select_offer", lambda *args, **kwargs: _sample_offer(), raising=False)
    monkeypatch.setattr(
        orch,
        "_resolve_bootstrap_script",
        lambda _config: "#!/usr/bin/env bash\nset -e\necho boot",
        raising=False,
    )

    cfg = _base_config()
    orch.run_orchestration(provider, cfg, _sample_models())

    assert len(provider.create_calls) == 1
    instance_config = provider.create_calls[0]["instance_config"]
    assert "idle_timeout_seconds" not in instance_config


def test_idle_timeout_propagation_is_deterministic_with_timeout_field(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    script = "#!/usr/bin/env bash\nset -e\necho boot"
    cfg = _config_with_timeout(1800)

    monkeypatch.setattr(orch, "select_offer", lambda *args, **kwargs: _sample_offer(), raising=False)
    monkeypatch.setattr(
        orch,
        "_resolve_bootstrap_script",
        lambda _config: script,
        raising=False,
    )

    orch.run_orchestration(provider, cfg, _sample_models())
    orch.run_orchestration(provider, cfg, _sample_models())

    assert len(provider.create_calls) == 2
    first_cfg = provider.create_calls[0]["instance_config"]
    second_cfg = provider.create_calls[1]["instance_config"]
    assert first_cfg == second_cfg
    assert first_cfg["idle_timeout_seconds"] == 1800
    assert first_cfg["bootstrap_script"] == script


def test_idle_timeout_instance_config_isolation_between_runs(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()
    cfg = _config_with_timeout(1800)

    monkeypatch.setattr(orch, "select_offer", lambda *args, **kwargs: _sample_offer(), raising=False)
    monkeypatch.setattr(
        orch,
        "_resolve_bootstrap_script",
        lambda _config: "#!/usr/bin/env bash\nset -e\necho boot",
        raising=False,
    )

    orch.run_orchestration(provider, cfg, _sample_models())
    first_cfg = provider.create_calls[0]["instance_config"]
    first_cfg["idle_timeout_seconds"] = 999

    orch.run_orchestration(provider, cfg, _sample_models())
    second_cfg = provider.create_calls[1]["instance_config"]

    assert id(first_cfg) != id(second_cfg)
    assert second_cfg["idle_timeout_seconds"] == 1800
