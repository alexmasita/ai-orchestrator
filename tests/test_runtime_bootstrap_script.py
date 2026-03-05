import importlib


SCRIPT_MODULE = "ai_orchestrator.runtime.script"


def _load_script_module():
    return importlib.import_module(SCRIPT_MODULE)


def _sample_config():
    return {"snapshot_version": "snap-v1"}


def _sample_models():
    return ["deepseek_llamacpp", "whisper"]


def _generate_script():
    module = _load_script_module()
    return module.generate_bootstrap_script(_sample_config(), _sample_models())


def test_runtime_script_module_import_path():
    module = _load_script_module()
    assert module.__name__ == SCRIPT_MODULE


def test_generate_bootstrap_script_exists():
    module = _load_script_module()
    assert hasattr(module, "generate_bootstrap_script")
    assert callable(module.generate_bootstrap_script)


def test_generate_bootstrap_script_returns_str():
    script = _generate_script()
    assert isinstance(script, str)


def test_script_starts_with_bash_shebang():
    script = _generate_script()
    assert script.startswith("#!/usr/bin/env bash")


def test_script_contains_set_e():
    script = _generate_script()
    assert "set -e" in script


def test_script_contains_install_commands():
    script = _generate_script()
    assert "apt update" in script
    assert "apt install" in script


def test_script_contains_required_repository_clones():
    script = _generate_script()
    assert "git clone https://github.com/ggerganov/llama.cpp" in script
    assert "git clone https://github.com/ggerganov/whisper.cpp" in script


def test_script_contains_deepseek_port_8080():
    script = _generate_script()
    assert "8080" in script


def test_script_contains_whisper_port_9000():
    script = _generate_script()
    assert "9000" in script


def test_script_contains_uvicorn_indicator():
    script = _generate_script()
    assert "uvicorn" in script


def test_script_contains_model_download_indicator():
    script = _generate_script()
    assert any(token in script for token in ("curl", "wget", "huggingface"))


def test_script_contains_llama_indicator():
    script = _generate_script()
    assert "llama" in script


def test_script_is_multiline():
    script = _generate_script()
    assert len(script.splitlines()) > 5


def test_script_is_deterministic_for_identical_inputs():
    module = _load_script_module()
    first = module.generate_bootstrap_script(_sample_config(), _sample_models())
    second = module.generate_bootstrap_script(_sample_config(), _sample_models())
    assert first == second


def test_script_has_no_leading_or_trailing_whitespace():
    script = _generate_script()
    assert script == script.strip()
