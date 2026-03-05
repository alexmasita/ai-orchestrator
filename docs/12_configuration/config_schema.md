Configuration Schema

The ai-orchestrator runtime is controlled through a single YAML configuration file, typically named:

config.yaml

The configuration file defines:

provider credentials

infrastructure constraints

GPU selection rules

model sizing parameters

orchestration runtime settings

The configuration is loaded by:

ai_orchestrator.config.load_config()

The resulting configuration object is a Python dictionary with normalized values.

Schema Overview

The configuration schema contains the following logical groups.

provider
gpu selection
network constraints
reliability constraints
pricing constraints
model sizing parameters
runtime configuration

Example structure:

vast_api_key: "<api key>"
vast_api_url: "https://console.vast.ai/api/v0"

gpu:
  min_vram_gb: 24
  preferred_models:
    - RTX_4090
    - RTX_A6000
    - A100

min_inet_down_mbps: 100
min_inet_up_mbps: 100

reliability_min: 0.98
verified_only: true

max_dph: 0.6
allow_interruptible: true

whisper_vram_gb: 8
whisper_disk_gb: 10

idle_timeout_seconds: 1800
snapshot_version: "v1"
Schema Rules
Required Fields

The following configuration fields are required:

vast_api_key
vast_api_url
gpu.min_vram_gb
max_dph
Conditional Fields

Some configuration fields are required only if specific models are used.

Example:

If CLI includes:

--models whisper

then the following configuration fields must exist:

whisper_vram_gb
whisper_disk_gb

If these fields are missing the system raises:

OrchestratorConfigError

during sizing.

Configuration Loading

Configuration is loaded through:

load_config(config_path)

Behavior:

YAML file parsed using PyYAML.

Values normalized.

URL normalization applied.

Result returned as dictionary.

Example:

config = load_config("config.yaml")
Validation Stage

Validation occurs in multiple layers.

Stage	Validator
config loading	config.py
sizing requirements	sizing.py
orchestration runtime	orchestrator.py

Each stage raises specific exceptions if invalid.

Error Types

Invalid configuration may raise:

ConfigError
OrchestratorConfigError

The CLI converts these to user-readable errors.