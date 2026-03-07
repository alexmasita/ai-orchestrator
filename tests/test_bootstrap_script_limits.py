from __future__ import annotations

import importlib

import pytest

from ai_orchestrator.runtime.script import render_bootstrap_script


ORCHESTRATOR_MODULE = "ai_orchestrator.orchestrator"
INTERFACE_MODULE = "ai_orchestrator.provider.interface"


def _load_orchestrator_module():
    return importlib.import_module(ORCHESTRATOR_MODULE)


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
        return interface.ProviderInstance(
            instance_id=f"mock-{offer_id}",
            gpu_name="RTX_4090",
            dph=0.5,
        )


def test_render_bootstrap_script_import_contract_callable():
    assert callable(render_bootstrap_script)


def test_render_bootstrap_script_byte_length_within_limit():
    script = render_bootstrap_script("#!/usr/bin/env bash\nset -e\necho boot\n", {"A": "1", "B": "2"})
    assert len(script.encode("utf-8")) <= 16384


def test_run_orchestration_rejects_oversized_script(monkeypatch):
    orch = _load_orchestrator_module()
    provider = _RecordingProvider()

    monkeypatch.setattr(
        orch,
        "_resolve_bootstrap_script",
        lambda _config: "A" * 20000,
        raising=False,
    )
    monkeypatch.setattr(
        orch,
        "select_offer",
        lambda *args, **kwargs: _sample_offer(),
        raising=False,
    )

    with pytest.raises(ValueError):
        orch.run_orchestration(provider, _sample_config(), ["deepseek_llamacpp", "whisper"])

    assert provider.create_calls == []


def test_render_bootstrap_script_is_utf8_encodable():
    script = render_bootstrap_script("#!/usr/bin/env bash\nset -e\necho boot\n", {"A": "1"})
    encoded = script.encode("utf-8")
    assert isinstance(encoded, bytes)


def test_render_bootstrap_script_is_deterministic_for_identical_inputs():
    base_script = "#!/usr/bin/env bash\nset -e\necho boot\n"
    first = render_bootstrap_script(base_script, {"A": "1", "B": "2"})
    second = render_bootstrap_script(base_script, {"A": "1", "B": "2"})
    assert first == second
