from __future__ import annotations

import importlib


def _load_orchestrator_module():
    try:
        return importlib.import_module("ai_orchestrator.orchestrator")
    except ModuleNotFoundError:
        return None


def test_combo2_readiness_requires_running_and_control_health_success():
    orchestrator = _load_orchestrator_module()
    assert orchestrator is not None, "Expected ai_orchestrator.orchestrator module"
    assert hasattr(
        orchestrator, "is_instance_ready"
    ), "Expected is_instance_ready(instance_payload, control_health_ok) contract"

    assert (
        orchestrator.is_instance_ready(
            {"actual_status": "running"},
            control_health_ok=True,
        )
        is True
    )

    assert (
        orchestrator.is_instance_ready(
            {"actual_status": "loading"},
            control_health_ok=True,
        )
        is False
    )


def test_combo2_readiness_running_state_alone_is_not_sufficient():
    orchestrator = _load_orchestrator_module()
    assert orchestrator is not None, "Expected ai_orchestrator.orchestrator module"
    assert hasattr(
        orchestrator, "is_instance_ready"
    ), "Expected is_instance_ready(instance_payload, control_health_ok) contract"

    result = orchestrator.is_instance_ready(
        {"actual_status": "running"},
        control_health_ok=False,
    )
    assert result is False
