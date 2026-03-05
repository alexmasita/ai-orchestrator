import importlib


BOOTSTRAP_MODULE = "ai_orchestrator.runtime.bootstrap"


def _load_bootstrap_module():
    return importlib.import_module(BOOTSTRAP_MODULE)


def test_bootstrap_module_import_path():
    module = _load_bootstrap_module()
    assert module.__name__ == BOOTSTRAP_MODULE


def test_bootstrap_functions_exist():
    module = _load_bootstrap_module()
    assert hasattr(module, "deepseek_start_command")
    assert callable(module.deepseek_start_command)
    assert hasattr(module, "whisper_start_command")
    assert callable(module.whisper_start_command)


def test_deepseek_start_command_contract():
    module = _load_bootstrap_module()
    command = module.deepseek_start_command()
    assert isinstance(command, list)
    assert all(isinstance(part, str) for part in command)
    assert "--host" in command
    assert "0.0.0.0" in command
    assert "--port" in command
    assert "8080" in command


def test_whisper_start_command_contract():
    module = _load_bootstrap_module()
    command = module.whisper_start_command()
    assert isinstance(command, list)
    assert all(isinstance(part, str) for part in command)
    assert "uvicorn" in command
    assert "--host" in command
    assert "0.0.0.0" in command
    assert "--port" in command
    assert "9000" in command


def test_bootstrap_commands_are_deterministic():
    module = _load_bootstrap_module()
    deepseek_a = module.deepseek_start_command()
    deepseek_b = module.deepseek_start_command()
    whisper_a = module.whisper_start_command()
    whisper_b = module.whisper_start_command()
    assert deepseek_a == deepseek_b
    assert whisper_a == whisper_b
