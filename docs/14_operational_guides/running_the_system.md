# Running the System

This document explains how to launch the `ai-orchestrator` system locally and what occurs during execution.

The CLI is the primary entrypoint to the orchestration system and is responsible for initiating the full infrastructure provisioning and runtime startup pipeline.

---

# Prerequisites

Before running the system, ensure the following prerequisites are satisfied.

## Python Environment

Create and activate a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
Install the Project

The project must be installed in editable mode so that the CLI entrypoint is available.

pip install -e .

This installs the console command:

ai-orchestrator

Verify installation:

which ai-orchestrator

Expected result:

.venv/bin/ai-orchestrator
Required Runtime Dependencies

The following dependencies must be installed:

requests
PyYAML

These are declared in pyproject.toml.

Configuration

The system is configured through config.yaml.

Example:

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

idle_timeout_seconds: 1800
snapshot_version: "v1"

whisper_vram_gb: 8
whisper_disk_gb: 10
Launch Command

To start the system:

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper

This launches the full orchestration pipeline.

Execution Flow

Running the command triggers the following sequence:

CLI
 ↓
load_config
 ↓
compute_requirements
 ↓
select_offer
 ↓
provider.search_offers
 ↓
provider.create_instance
 ↓
bootstrap script injection
 ↓
runtime startup
 ↓
healthcheck readiness
 ↓
CLI prints result JSON
Optional Launch Script

The repository includes launch.sh for convenience.

Example:

./launch.sh

The script internally runs:

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper
Successful Run

On success, the CLI prints a JSON object describing the running instance.

Example:

{
  "cost_per_hour": 0.52,
  "deepseek_url": "http://1.2.3.4:8080",
  "gpu_type": "RTX_4090",
  "idle_timeout": 1800,
  "instance_id": "abc123",
  "snapshot_version": "v1",
  "whisper_url": "http://1.2.3.4:9000"
}

This indicates:

the instance was successfully created

runtime services are available

readiness checks passed

Shutdown Behavior

The orchestrator itself does not maintain long-running state.

Instances remain running until:

idle timeout triggers shutdown

user manually stops the instance

provider lifecycle ends the instance