import importlib
from pathlib import Path

import pytest


CONFIG_MODULE = "ai_orchestrator.config"

REQUIRED_CONFIG_FIELDS = [
    "vast_api_key",
    "vast_api_url",
    "snapshot_version",
    "idle_timeout_seconds",
    "min_reliability",
    "min_inet_up_mbps",
    "min_inet_down_mbps",
    "allow_interruptible",
    "max_dph",
]


def _load_config_module():
    return importlib.import_module(CONFIG_MODULE)


def _valid_config_dict():
    return {
        "vast_api_key": "key-123",
        "vast_api_url": "https://vast.example/api",
        "snapshot_version": "snap-v1",
        "idle_timeout_seconds": 1800,
        "min_reliability": 0.95,
        "min_inet_up_mbps": 100.0,
        "min_inet_down_mbps": 100.0,
        "allow_interruptible": True,
        "max_dph": 2.0,
    }


def _write_yaml(path: Path, data: dict):
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_config_module_import_path():
    module = _load_config_module()
    assert module.__name__ == CONFIG_MODULE


def test_load_config_returns_dict_for_valid_yaml(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, _valid_config_dict())

    loaded = module.load_config(str(config_path))
    assert isinstance(loaded, dict)


def test_load_config_contains_all_required_fields(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, _valid_config_dict())

    loaded = module.load_config(str(config_path))
    for field in REQUIRED_CONFIG_FIELDS:
        assert field in loaded


@pytest.mark.parametrize("missing_field", REQUIRED_CONFIG_FIELDS)
def test_load_config_missing_required_field_raises_config_error(tmp_path, missing_field):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    data = _valid_config_dict()
    del data[missing_field]
    _write_yaml(config_path, data)

    with pytest.raises(module.ConfigError):
        module.load_config(str(config_path))


def test_load_config_uses_yaml_safe_load(monkeypatch, tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, _valid_config_dict())

    expected = _valid_config_dict()
    calls = {"count": 0}

    def _fake_safe_load(stream):
        calls["count"] += 1
        _ = stream.read()
        return expected

    monkeypatch.setattr(module.yaml, "safe_load", _fake_safe_load)

    loaded = module.load_config(str(config_path))
    assert calls["count"] == 1
    assert loaded == expected


def test_load_config_is_deterministic_for_identical_file(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, _valid_config_dict())

    first = module.load_config(str(config_path))
    second = module.load_config(str(config_path))
    assert first == second


def test_load_config_strips_double_quoted_vast_api_url(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                'vast_api_key: "key-123"',
                'vast_api_url: "https://console.vast.ai/api/v0"',
                'snapshot_version: "v1"',
                "idle_timeout_seconds: 1800",
                "min_reliability: 0.98",
                "min_inet_up_mbps: 100",
                "min_inet_down_mbps: 100",
                "allow_interruptible: true",
                "max_dph: 2.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = module.load_config(str(config_path))
    assert loaded["vast_api_url"] == "https://console.vast.ai/api/v0"


def test_load_config_strips_single_quoted_vast_api_url(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "vast_api_key: 'key-123'",
                "vast_api_url: 'https://console.vast.ai/api/v0'",
                "snapshot_version: 'v1'",
                "idle_timeout_seconds: 1800",
                "min_reliability: 0.98",
                "min_inet_up_mbps: 100",
                "min_inet_down_mbps: 100",
                "allow_interruptible: true",
                "max_dph: 2.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = module.load_config(str(config_path))
    assert loaded["vast_api_url"] == "https://console.vast.ai/api/v0"


def test_load_config_parses_other_scalar_types_correctly(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "vast_api_key: key-123",
                'vast_api_url: "https://console.vast.ai/api/v0"',
                "snapshot_version: v1",
                "idle_timeout_seconds: 1800",
                "min_reliability: 0.98",
                "min_inet_up_mbps: 100",
                "min_inet_down_mbps: 100",
                "allow_interruptible: true",
                "max_dph: 2.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = module.load_config(str(config_path))
    assert isinstance(loaded["snapshot_version"], str)
    assert isinstance(loaded["idle_timeout_seconds"], int)
    assert isinstance(loaded["min_reliability"], float)
    assert isinstance(loaded["allow_interruptible"], bool)
    assert isinstance(loaded["max_dph"], float)


def test_load_config_normalizes_vast_api_url_no_trailing_slash(tmp_path):
    module = _load_config_module()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "vast_api_key: key-123",
                'vast_api_url: "https://console.vast.ai/api/v0/"',
                "snapshot_version: v1",
                "idle_timeout_seconds: 1800",
                "min_reliability: 0.98",
                "min_inet_up_mbps: 100",
                "min_inet_down_mbps: 100",
                "allow_interruptible: true",
                "max_dph: 2.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = module.load_config(str(config_path))
    assert loaded["vast_api_url"] == "https://console.vast.ai/api/v0"
