Instance Lifecycle
Offer Discovered
      ↓
Offer Selected
      ↓
Instance Created
      ↓
Bootstrap Script Executed
      ↓
Runtime Services Start
      ↓
Healthcheck Pass
      ↓
Instance Ready
Stage 1 — Instance Creation

The provider creates the instance.

PUT /asks/{id}

The response contains:

new_contract
Stage 2 — Instance Metadata

The provider retrieves instance details.

GET /instances/{id}

This returns:

gpu_name
dph
public_ip
Stage 3 — Bootstrap Execution

The injected script performs:

environment preparation
model installation
service launch
Stage 4 — Runtime Services

Expected services:

DeepSeek → port 8080
Whisper → port 9000
Stage 5 — Healthchecks

The orchestrator waits for readiness.