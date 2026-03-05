Purpose

The Orchestrator Core is the central coordination layer of the ai-orchestrator system.

It is responsible for transforming a high-level CLI request into a running GPU instance capable of serving inference workloads.

The orchestrator does not directly run models, communicate with APIs, or implement runtime logic. Instead it coordinates the following subsystems:

CLI
 ↓
Config Loader
 ↓
Sizing Engine
 ↓
Offer Selection
 ↓
Provider Instance Creation
 ↓
Bootstrap Script Injection
 ↓
Runtime Healthchecks
 ↓
CLI Output

The orchestrator acts as the control plane of the system.

Core Responsibilities

The orchestrator performs the following responsibilities in strict order:

Validate configuration inputs

Resolve model resource requirements

Find matching provider offers

Select the optimal GPU instance

Generate deterministic bootstrap script

Create provider instance

Inject bootstrap startup logic

Wait for runtime readiness

Return structured instance metadata

Each of these responsibilities is implemented in a deterministic way to support reproducible infrastructure launches.

Key Entry Point

The orchestrator exposes a single public function:

run_orchestration(provider, config, models)

This function is called from the CLI layer.

Orchestrator Boundaries

The orchestrator does not perform:

Responsibility	Location
Model sizing logic	sizing.py
Bootstrap script creation	runtime/bootstrap.py
Provider API logic	provider/
Model runtime logic	plugins/
Health checks	runtime/healthcheck.py

This strict separation prevents architectural drift.

Data Flow

Primary data objects used inside orchestration:

Config

Loaded configuration from config.yaml.

Contains:

vast_api_key
vast_api_url
gpu constraints
network constraints
max_dph
idle_timeout_seconds
snapshot_version
model sizing parameters
SizingResult

Produced by:

compute_requirements(SizingInput)

Contains:

required_vram_gb
required_disk_gb
required_models
network_requirements
ProviderOffer

Represents a GPU offer returned from a provider.

Fields:

id
gpu_name
vram_gb
dph
reliability
interruptible
inet_down
inet_up
ProviderInstance

Returned after instance creation.

Fields:

instance_id
gpu_name
dph
public_ip
Deterministic Design

The orchestrator is explicitly designed to guarantee deterministic behavior:

Guarantee	Mechanism
Offer selection determinism	stable ordering
Bootstrap determinism	deterministic script generator
Instance config determinism	identical input → identical payload
CLI output determinism	sorted JSON serialization
Test determinism	no real network usage

This guarantees predictable infrastructure launches.

Execution Contract

The orchestrator must guarantee:

Input:
  provider
  config
  models

Output:
  instance metadata

Example return payload:

{
  "instance_id": "abc123",
  "gpu_name": "RTX_4090",
  "dph": 0.72,
  "idle_timeout": 1800,
  "snapshot_version": "v1",
  "deepseek_url": "http://1.2.3.4:8080",
  "whisper_url": "http://1.2.3.4:9000"
}
Debug Mode

If the environment variable is set:

AI_ORCH_DEBUG=1

The orchestrator emits runtime diagnostics to stderr only.

This ensures:

JSON output remains valid

debug logs never corrupt CLI output

Example logs:

Selected offer: RTX_4090 $0.72
Instance created: abc123
Waiting for readiness...
DeepSeek ready
Whisper ready