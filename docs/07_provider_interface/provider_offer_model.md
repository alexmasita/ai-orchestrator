# ProviderOffer Model

## Purpose

`ProviderOffer` represents a GPU offer returned by an infrastructure provider marketplace.

The orchestrator uses these offers to select the most suitable compute resource.

---

# Data Structure

```python
ProviderOffer(
    id: str,
    gpu_name: str,
    gpu_ram_gb: int,
    dph: float,
    reliability: float,
    interruptible: bool
)
Field Definitions
id

Unique identifier of the offer.

Example:

ask_contract_id

Used later when creating instances.

gpu_name

Name of the GPU.

Examples:

RTX_4090
A100
RTX_A6000
gpu_ram_gb

Amount of VRAM available.

Example:

24

Used to validate model requirements.

dph

Cost per hour.

Example:

0.72

Lower cost offers are preferred when multiple candidates satisfy requirements.

reliability

Provider reliability score.

Example:

0.99

Offers below the configured reliability threshold are rejected.

interruptible

Whether the instance can be preempted.

Example:

true

Interruptible instances are cheaper but may be terminated.

Determinism Rules

Offer lists must:

preserve provider API ordering

not introduce randomness

remain stable across identical queries

The orchestrator performs final selection deterministically.