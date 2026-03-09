Purpose

This document explains how to run the ai-orchestrator system locally after installation.

Required Files

Before running, ensure the repository contains:

config.yaml
launch.sh
Example Configuration

config.yaml example:

vast_api_key: "<your_api_key>"
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
Running the CLI Directly

Example:

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper
Using the Launch Script

The repository includes a helper script:

launch.sh

Run:

./launch.sh

This executes the CLI with the standard configuration.

Debug Mode

To enable verbose orchestration logging:

AI_ORCH_DEBUG=1 ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper

Debug output includes:

selected GPU offer

provider request endpoints

readiness checks

service URLs

Debug logs are written to stderr.

Expected Successful Output

Example output:

{
  "instance_id": "12345",
  "gpu_type": "RTX_4090",
  "cost_per_hour": 0.55,
  "idle_timeout": 1800,
  "snapshot_version": "v1",
  "deepseek_url": "http://34.10.20.5:8080",
  "whisper_url": "http://34.10.20.5:9000"
}
Common Startup Failures
Missing dependencies
Provider error: requests dependency is missing

Fix:

pip install -e .
Missing model configuration
Configuration error: Missing whisper config

Add to config.yaml:

whisper_vram_gb
whisper_disk_gb
Network or DNS failure

Example:

Provider error: Vast /bundles request failed

Check connectivity:

curl https://console.vast.ai
Summary

Running locally requires:

Python virtual environment

Editable installation

Valid config.yaml

Vast API connectivity

Once these are satisfied, the system can be launched with:

ai-orchestrator start --config config.yaml --models deepseek_llamacpp whisper