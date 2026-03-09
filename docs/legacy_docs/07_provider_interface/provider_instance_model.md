# ProviderInstance Model

## Purpose

`ProviderInstance` represents a **running compute instance** returned by an infrastructure provider.

It contains the minimal metadata required for orchestration and CLI output.

The model is intentionally small and stable to avoid provider-specific coupling.

---

# Data Structure

```python
ProviderInstance(
    instance_id: str,
    gpu_name: str,
    dph: float,
    public_ip: Optional[str] = None
)
Field Definitions
instance_id

Unique identifier for the running instance.

Example:

abc123

Used for:

provider management

instance lookup

debugging

gpu_name

Human-readable GPU type.

Examples:

RTX_4090
RTX_A6000
A100

The CLI maps this field to:

gpu_type
dph

Cost per hour.

Example:

0.72

The CLI maps this field to:

cost_per_hour
public_ip

Public IP address of the instance.

Example:

1.2.3.4

This is used to construct service URLs:

http://<ip>:8080
http://<ip>:9000

If not available, the orchestrator may fall back to:

127.0.0.1
Determinism Requirements

Instances must always be returned with:

deterministic field ordering

stable field names

no provider-specific metadata

Provider-specific fields must not be exposed to the orchestrator.

Backward Compatibility

Future providers may add additional metadata internally, but the orchestrator relies only on:

instance_id
gpu_name
dph
public_ip

These fields must remain stable.