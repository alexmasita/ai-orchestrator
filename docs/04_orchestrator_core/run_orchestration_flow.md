Overview

run_orchestration() implements the full lifecycle of provisioning a GPU instance and preparing it for model inference.

Function Signature
run_orchestration(
    provider,
    config,
    models,
    *,
    sizing_result=None,
    required_vram_gb=None,
    idle_timeout=None,
    snapshot_version=None
)
Execution Steps
Step 1 — Validate Idle Timeout

The orchestrator validates the idle timeout configuration.

Requirements:

type(value) == int
value > 0

Invalid values raise:

ValueError

This validation occurs before any provider interaction.

Step 2 — Compute Resource Requirements

If no sizing_result is provided:

compute_requirements(SizingInput)

Inputs:

models
config

Output:

required_vram_gb
required_disk_gb
Step 3 — Select GPU Offer

The orchestrator requests offers from the provider.

provider.search_offers()

These offers are filtered according to system constraints.

Selection is deterministic.

Step 4 — Generate Bootstrap Script

A runtime startup script is generated.

generate_bootstrap_script(config, models)

The script performs:

system setup
model download
service startup
port binding
Step 5 — Construct Instance Config

The orchestrator builds a provider payload:

instance_config = {
    "bootstrap_script": script,
    "idle_timeout_seconds": idle_timeout
}

The config object is rebuilt every run to ensure no mutation leakage.

Step 6 — Create Instance

The provider creates the instance.

provider.create_instance(
    offer_id,
    snapshot_version,
    instance_config
)

The provider returns a ProviderInstance.

Step 7 — Compute Runtime URLs

Service endpoints are generated:

deepseek_url = http://{ip}:8080
whisper_url = http://{ip}:9000

IP resolution priority:

instance.public_ip
instance.ip
fallback: 127.0.0.1
Step 8 — Runtime Readiness

The orchestrator blocks until services respond.

wait_for_instance_ready(ip, deepseek_url, whisper_url)

Failure raises:

RuntimeError
Step 9 — Return Result

The orchestrator returns instance metadata to the CLI.