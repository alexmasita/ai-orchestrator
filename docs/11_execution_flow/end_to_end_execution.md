# End-to-End Execution Flow

This document describes the full runtime execution path of the `ai-orchestrator` system from CLI invocation to instance readiness.

The orchestration system provisions GPU infrastructure, deploys runtime services, verifies readiness, and returns connection endpoints to the user.

The system is designed to maintain:

• deterministic behavior  
• strict separation of layers  
• reproducible runtime environments  
• provider abstraction  

---

# High-Level Execution Pipeline


User CLI Command
↓
CLI Layer
↓
Configuration Loading
↓
Sizing Engine
↓
Offer Selection
↓
Provider Instance Creation
↓
Bootstrap Injection
↓
Instance Readiness Checks
↓
CLI Output


Each stage operates under strict input/output contracts.

---

# Step 1 — CLI Invocation

The user launches orchestration through the CLI command:


ai-orchestrator start --config config.yaml --models deepseek_llamacpp whisper


The CLI performs the following steps:

1. Parse command-line arguments
2. Load configuration
3. Construct sizing input
4. Execute orchestration
5. Format final output

The CLI **does not contain orchestration logic**.

It only coordinates system components.

---

# Step 2 — Configuration Loading

Configuration is loaded using:


load_config(config_path)


Responsibilities:

• parse YAML configuration  
• normalize values  
• validate required keys  

Normalization rules include:

• stripping quotes
• removing trailing slashes
• converting numeric values

Example configuration fields:


vast_api_key
vast_api_url
gpu.min_vram_gb
max_dph
idle_timeout_seconds


Output:


Dict[str, Any]


---

# Step 3 — Sizing Engine

The sizing engine computes the **minimum infrastructure requirements**.

Function:


compute_requirements(sizing_input)


Input:


SizingInput:
models: List[str]
config: Dict


Output:


SizingResult:
required_vram_gb
required_disk_gb
required_inet_down
required_inet_up


Each model plugin contributes resource requirements.

Example:

| Model | VRAM |
|------|------|
DeepSeek | ~20 GB |
Whisper | ~8 GB |

The sizing engine aggregates these requirements.

---

# Step 4 — Offer Search

The orchestrator queries the provider for matching GPU offers.


provider.search_offers(requirements)


For Vast this corresponds to:


POST /api/v0/bundles/


Search filters include:

• GPU VRAM
• reliability
• network speed
• verified hosts
• price limits

Provider responses are parsed into internal objects:


ProviderOffer


Offers are **not sorted by provider**.

Selection logic occurs in the orchestrator.

---

# Step 5 — Offer Selection

The orchestrator selects the optimal GPU offer.


select_offer(offers, requirements)


Selection criteria:

1. meets VRAM requirement
2. meets reliability requirement
3. meets network requirements
4. price <= max_dph
5. preferred GPU models (if configured)

The first valid offer is selected.

This ensures deterministic selection behavior.

---

# Step 6 — Instance Creation

The provider is instructed to create an instance.


provider.create_instance(
offer_id,
snapshot_version,
instance_config
)


Instance configuration contains:


{
bootstrap_script: "...",
idle_timeout_seconds: 1800
}


For Vast this corresponds to:


PUT /api/v0/asks/{offer_id}


The request injects:

• container image
• runtime type
• environment variables
• bootstrap commands

---

# Step 7 — Bootstrap Injection

A runtime bootstrap script is injected into the instance.

The script performs:

1. environment preparation
2. model runtime startup
3. port exposure
4. service initialization

Services launched:

| Service | Port |
|-------|------|
DeepSeek | 8080 |
Whisper | 9000 |

Bootstrap scripts are generated deterministically.

Script size limit:


MAX_BOOTSTRAP_SCRIPT_BYTES = 16384


---

# Step 8 — Instance Readiness Checks

Once the instance is created, readiness checks are performed.


wait_for_instance_ready(ip, deepseek_url, whisper_url)


Checks include:

1. TCP port availability
2. HTTP endpoint health

Example endpoints:


http://{ip}:8080
http://{ip}:9000


Failures raise:


RuntimeError


---

# Step 9 — CLI Output

After readiness checks succeed the CLI prints a JSON result.

Example:


{
"instance_id": "12345",
"gpu_type": "RTX_4090",
"cost_per_hour": 0.72,
"idle_timeout": 1800,
"snapshot_version": "v1",
"deepseek_url": "http://1.2.3.4:8080
",
"whisper_url": "http://1.2.3.4:9000
"
}


The output is deterministic and sorted.


json.dumps(result, sort_keys=True)


---

# System Guarantees

The execution flow guarantees:

• deterministic infrastructure selection  
• reproducible runtime environment  
• isolated provider layer  
• explicit error propagation  

---

# Summary

The orchestration pipeline transforms a CLI command into a fully operational AI inference instance.


CLI
→ configuration
→ sizing
→ provider offer search
→ instance creation
→ bootstrap runtime
→ readiness verification
→ JSON result


Every step operates under strict contracts to prevent architectural drift.