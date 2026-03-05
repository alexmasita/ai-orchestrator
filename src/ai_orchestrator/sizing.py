from dataclasses import dataclass
from math import ceil

from ai_orchestrator.plugins.registry import get_plugin_by_name


class OrchestratorConfigError(Exception):
    pass


@dataclass(init=False)
class SizingInput:
    models: list[str]
    config: dict

    def __init__(self, models=None, config=None, model_name=None):
        if models is None:
            if model_name is None:
                raise TypeError("Either models or model_name must be provided")
            models = [model_name]
        elif model_name is not None:
            raise TypeError("Provide either models or model_name, not both")
        self.models = list(models)
        self.config = config


@dataclass
class SizingResult:
    vram_gb: int
    disk_gb: int


def _resolve_plugin_name(model_name: str) -> str:
    if model_name == "deepseek_llamacpp":
        return "deepseek"
    return model_name


def compute_requirements(sizing_input: SizingInput) -> SizingResult:
    config = sizing_input.config
    if config is None:
        raise OrchestratorConfigError("Missing config")

    total_vram = 0
    total_disk = 0

    for model_name in sizing_input.models:
        if model_name == "whisper":
            if "whisper_vram_gb" not in config or "whisper_disk_gb" not in config:
                raise OrchestratorConfigError("Missing whisper config")
            total_vram += int(config["whisper_vram_gb"])
            total_disk += int(config["whisper_disk_gb"])
            continue

        plugin_cls = get_plugin_by_name(_resolve_plugin_name(model_name))
        plugin = plugin_cls()
        total_vram += int(plugin.required_vram_gb(config))
        total_disk += int(plugin.required_disk_gb(config))

    return SizingResult(vram_gb=int(ceil(total_vram * 1.15)), disk_gb=int(total_disk))
