import dataclasses
import importlib
import math

import pytest


SIZING_MODULE = "ai_orchestrator.sizing"


def _load_sizing_module():
    return importlib.import_module(SIZING_MODULE)


def _valid_sizing_input(module):
    return module.SizingInput(
        model_name="deepseek_llamacpp",
        config={"quantization": "Q4_K_M"},
    )


def test_sizing_module_import_path():
    module = _load_sizing_module()
    assert module.__name__ == SIZING_MODULE


def test_sizing_input_is_dataclass():
    module = _load_sizing_module()
    assert hasattr(module, "SizingInput")
    assert dataclasses.is_dataclass(module.SizingInput)


def test_compute_requirements_exists():
    module = _load_sizing_module()
    assert hasattr(module, "compute_requirements")
    assert callable(module.compute_requirements)


def test_compute_requirements_applies_vram_buffer_and_ceil_rounding():
    module = _load_sizing_module()
    sizing_input = _valid_sizing_input(module)
    result = module.compute_requirements(sizing_input)
    assert result.vram_gb == math.ceil(26 * 1.15)


def test_compute_requirements_returns_int_fields():
    module = _load_sizing_module()
    sizing_input = _valid_sizing_input(module)
    result = module.compute_requirements(sizing_input)
    assert isinstance(result.vram_gb, int)
    assert isinstance(result.disk_gb, int)


def test_compute_requirements_is_deterministic_for_identical_inputs():
    module = _load_sizing_module()
    sizing_input = _valid_sizing_input(module)
    first = module.compute_requirements(sizing_input)
    second = module.compute_requirements(sizing_input)
    assert first == second


def test_compute_requirements_missing_config_raises_orchestrator_config_error():
    module = _load_sizing_module()
    sizing_input = module.SizingInput(model_name="deepseek_llamacpp", config=None)
    with pytest.raises(module.OrchestratorConfigError):
        module.compute_requirements(sizing_input)


def test_compute_requirements_unknown_model_raises_key_error():
    module = _load_sizing_module()
    sizing_input = module.SizingInput(
        model_name="__unknown_model__",
        config={"quantization": "Q4_K_M"},
    )
    with pytest.raises(KeyError):
        module.compute_requirements(sizing_input)
