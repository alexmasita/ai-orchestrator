Purpose

The Sizing Engine determines the minimum compute resources required to run the requested models before infrastructure provisioning begins.

It transforms:

requested models
+
configuration constraints

into a deterministic resource requirement object used by the orchestrator to select a compatible GPU instance.

The sizing engine runs before provider interaction and acts as a hard gate to prevent invalid orchestration requests.

Responsibilities

The sizing engine is responsible for:

Determining required VRAM

Determining required disk

Validating model configuration

Enforcing config contract requirements

Producing a deterministic SizingResult

It does not:

communicate with providers

provision infrastructure

choose specific GPUs

perform runtime bootstrapping

Those responsibilities belong to the orchestrator and provider layers.

Primary Entry Point
compute_requirements(SizingInput) → SizingResult

Defined in:

src/ai_orchestrator/sizing.py
Input Object
SizingInput
SizingInput(
    models: List[str],
    config: dict
)

Fields:

Field	Description
models	list of requested models
config	loaded configuration

Example:

SizingInput(
    models=["deepseek_llamacpp", "whisper"],
    config=config_dict
)
Output Object
SizingResult

The result object contains aggregated requirements.

Typical structure:

SizingResult(
    required_vram_gb: int,
    required_disk_gb: int,
    required_network_down_mbps: float,
    required_network_up_mbps: float
)

This result feeds directly into the orchestrator’s offer filtering logic.

Determinism Guarantee

The sizing engine must be deterministic.

Identical inputs must produce identical results.

Determinism is enforced through:

fixed plugin registry

deterministic aggregation logic

absence of randomness

absence of system-state dependence

Sizing Pipeline

The sizing process follows this pipeline:

models requested
        ↓
plugin registry lookup
        ↓
collect model requirements
        ↓
aggregate resource requirements
        ↓
validate configuration
        ↓
return SizingResult
Aggregation Rules

For multiple models:

VRAM
required_vram = max(model_vram)

Reason:

Models run concurrently but share GPU memory pools differently.
The design assumes the largest model dominates GPU memory usage.

Disk
required_disk = sum(model_disk)

Reason:

Each model requires separate runtime artifacts.

Network

Network requirements come from configuration:

min_inet_down_mbps
min_inet_up_mbps
Model Registry Interaction

The sizing engine retrieves model requirements via the plugin registry:

plugins.registry.get_plugin(model_name)

Each plugin provides resource requirements.

Configuration Dependency

Certain models require configuration fields.

Example:

whisper_vram_gb
whisper_disk_gb

If these fields are missing, sizing fails.

Failure Conditions

Sizing fails if:

a model is unknown

required config fields are missing

config values are invalid

Errors raised:

OrchestratorConfigError
Testing Strategy

Tests located in:

tests/test_sizing_engine.py

Test guarantees:

deterministic output

correct aggregation

correct error handling

plugin contract adherence

Design Rationale

Sizing exists as a separate layer to ensure:

provider independence

predictable orchestration

early configuration validation

This prevents wasted provider calls and runtime failures.