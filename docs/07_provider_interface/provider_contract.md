# Provider Interface Contract

## Purpose

The provider interface defines the contract between the **orchestration engine** and the **infrastructure layer** responsible for provisioning compute resources.

This abstraction allows the orchestrator to remain **provider-agnostic**, enabling support for multiple infrastructure backends such as:

- Vast.ai
- AWS
- GCP
- On-prem GPU clusters
- Local testing providers

The orchestrator interacts with providers exclusively through this interface.

No provider-specific code exists inside the orchestrator.

---

# Provider Responsibilities

A provider implementation must support the following responsibilities:

1. **Offer Discovery**
2. **Instance Provisioning**
3. **Instance Metadata Resolution**

The provider must expose a stable interface that the orchestrator can call.

---

# Required Methods

Every provider must implement the following methods.

## search_offers(requirements)

Search the provider marketplace for available GPU offers that satisfy the orchestration requirements.

### Input

```python
requirements: dict

Example:

{
    "required_vram_gb": 24
}
Output

Returns an iterable of ProviderOffer objects.

Example:

[
    ProviderOffer(
        id="1234",
        gpu_name="RTX_4090",
        gpu_ram_gb=24,
        dph=0.72,
        reliability=0.99,
        interruptible=True
    )
]
Behavior

Providers must:

return all offers matching requirements

preserve deterministic ordering from provider API responses

not perform additional filtering beyond requirements

Filtering logic is handled by the orchestrator.

create_instance(offer_id, snapshot_version, instance_config)

Creates a new compute instance using a specific GPU offer.

Input
offer_id: str
snapshot_version: str
instance_config: dict

Example:

instance_config = {
    "bootstrap_script": "...",
    "idle_timeout_seconds": 1800
}
Behavior

The provider must:

Start the instance using the specified offer

Inject the bootstrap script

Apply runtime configuration

Return a ProviderInstance

Output
ProviderInstance(
    instance_id="abc123",
    gpu_name="RTX_4090",
    dph=0.72,
    public_ip="1.2.3.4"
)

The instance must be returned before readiness checks occur.

Determinism Requirements

Providers must not introduce nondeterministic behavior.

Specifically:

Providers must NOT:

randomize offer ordering

inject timestamps into outputs

modify bootstrap scripts

reorder instance configuration fields

Error Handling Requirements

Providers must convert infrastructure errors into ProviderError subclasses.

Never allow raw library exceptions to escape the provider layer.

Examples:

Bad:

requests.exceptions.ConnectionError

Correct:

raise VastProviderError("Vast API connection failed")
Security Requirements

Providers must never leak sensitive information.

Forbidden in logs or exceptions:

API keys

authentication tokens

provider credentials

Future Provider Compatibility

All providers must maintain compatibility with:

ProviderOffer
ProviderInstance
ProviderError

These structures define the stable contract between orchestration and infrastructure.