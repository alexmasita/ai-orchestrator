Purpose

VRAM calculation determines the minimum GPU memory required to run the selected models.

This is the primary constraint used when selecting GPU offers.

VRAM Sources

VRAM requirements come from:

model plugins

configuration overrides

Example configuration:

whisper_vram_gb: 8
Plugin VRAM Reporting

Each plugin exposes required VRAM.

Example:

DeepSeek plugin
Whisper plugin
Aggregation Rule

VRAM is computed as:

required_vram = max(plugin_vram_requirements)

Reason:

GPU VRAM is shared between processes, but the system assumes worst-case allocation.

Example

Requested models:

deepseek_llamacpp
whisper

Plugin requirements:

deepseek → 16GB
whisper → 8GB

Result:

required_vram = 16GB
Why Not Sum VRAM?

Summing VRAM would:

drastically overestimate requirements

eliminate viable GPUs

increase infrastructure cost

The design assumes memory reuse across processes.

Edge Cases

Failure occurs if:

VRAM config values are missing

VRAM config values are invalid

Example error:

OrchestratorConfigError("Missing whisper config")