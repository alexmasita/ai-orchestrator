from __future__ import annotations

from pathlib import Path

import yaml


def test_neuroflow_combo_assets_present_and_wired():
    combo_yaml_path = Path("combos") / "neuroflow" / "combo.yaml"
    bootstrap_path = Path("combos") / "neuroflow" / "bootstrap.sh"
    config_path = Path("configs") / "neuroflow.yaml"

    assert combo_yaml_path.is_file(), "Expected combos/neuroflow/combo.yaml asset"
    assert bootstrap_path.is_file(), "Expected combos/neuroflow/bootstrap.sh asset"
    assert config_path.is_file(), "Expected configs/neuroflow.yaml runtime config asset"

    combo_manifest = yaml.safe_load(combo_yaml_path.read_text(encoding="utf-8"))
    assert combo_manifest["name"] == "neuroflow"
    assert combo_manifest["provider"] == "vast"

    services = combo_manifest.get("services", {})
    assert list(services.keys()) == [
        "interpret",
        "reasoner",
        "rerank",
        "stt",
        "tts",
        "control",
    ]
    assert services["interpret"]["port"] == 8080
    assert services["reasoner"]["port"] == 8081
    assert services["rerank"]["port"] == 8082
    assert services["stt"]["port"] == 9000
    assert services["tts"]["port"] == 9001
    assert services["control"]["port"] == 7999

    runtime_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert runtime_config["snapshot_version"] == "v2-neuroflow-dev-80gb"
    assert runtime_config["allow_interruptible"] is True
    assert isinstance(runtime_config["verified_only"], bool)
    assert float(runtime_config["max_dph"]) > 0.0
    assert runtime_config["idle_timeout_seconds"] == 1200
    assert runtime_config["instance_ready_timeout_seconds"] == 2400
    assert runtime_config["bootstrap_base_url"].startswith("https://raw.githubusercontent.com/")
    assert int(runtime_config["min_disk_gb"]) >= 300

    bootstrap_contents = bootstrap_path.read_text(encoding="utf-8")
    assert "--runner pooling" in bootstrap_contents
    assert 'STT_MODEL="${AI_ORCH_STT_MODEL:-turbo}"' in bootstrap_contents
    assert "python3 - <<PY" in bootstrap_contents
    assert "uv venv .venv" in bootstrap_contents
    assert 'uv run --no-sync uvicorn api.src.main:app \\' in bootstrap_contents
    assert '--include "chat_template.jinja"' in bootstrap_contents
    assert '--include "model.safetensors"' in bootstrap_contents
    assert 'rm -rf "$MODELS_DIR/rerank/.cache"' in bootstrap_contents
