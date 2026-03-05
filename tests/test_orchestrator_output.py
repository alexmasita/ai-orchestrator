import importlib


ORCHESTRATOR_MODULE = "ai_orchestrator.orchestrator"


def _load_orchestrator_module():
    return importlib.import_module(ORCHESTRATOR_MODULE)


class _StubProvider:
    pass


def test_run_orchestration_returns_exact_output_keys():
    orch = _load_orchestrator_module()
    result = orch.run_orchestration(
        provider=_StubProvider(),
        required_vram_gb=26,
        config={
            "min_reliability": 0.9,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 3.0,
        },
        idle_timeout=1800,
        snapshot_version="v1",
    )
    assert set(result.keys()) == {
        "instance_id",
        "gpu_type",
        "cost_per_hour",
        "idle_timeout",
        "snapshot_version",
    }


def test_run_orchestration_has_no_additional_keys():
    orch = _load_orchestrator_module()
    result = orch.run_orchestration(
        provider=_StubProvider(),
        required_vram_gb=26,
        config={
            "min_reliability": 0.9,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 3.0,
        },
        idle_timeout=1800,
        snapshot_version="v1",
    )
    assert len(result.keys()) == 5


def test_run_orchestration_output_value_types():
    orch = _load_orchestrator_module()
    result = orch.run_orchestration(
        provider=_StubProvider(),
        required_vram_gb=26,
        config={
            "min_reliability": 0.9,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 3.0,
        },
        idle_timeout=1800,
        snapshot_version="v1",
    )
    assert isinstance(result["instance_id"], str)
    assert isinstance(result["gpu_type"], str)
    assert isinstance(result["cost_per_hour"], float)
    assert isinstance(result["idle_timeout"], int)
    assert isinstance(result["snapshot_version"], str)


def test_run_orchestration_is_deterministic_for_identical_inputs():
    orch = _load_orchestrator_module()
    kwargs = {
        "provider": _StubProvider(),
        "required_vram_gb": 26,
        "config": {
            "min_reliability": 0.9,
            "min_inet_up_mbps": 100.0,
            "min_inet_down_mbps": 100.0,
            "allow_interruptible": True,
            "max_dph": 3.0,
        },
        "idle_timeout": 1800,
        "snapshot_version": "v1",
    }
    first = orch.run_orchestration(**kwargs)
    second = orch.run_orchestration(**kwargs)
    assert first == second
