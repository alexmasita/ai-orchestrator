# Mock Provider

## Purpose

The mock provider implements the provider interface without interacting with real infrastructure.

It is used for:

- deterministic tests
- development environments
- CLI behavior verification

---

# Location


src/ai_orchestrator/provider/mock.py


---

# Behavior

The mock provider returns predictable values.

Example offer:


ProviderOffer(
id="mock_offer",
gpu_name="RTX_4090",
gpu_ram_gb=24,
dph=0.50,
reliability=0.99,
interruptible=True
)


Example instance:


ProviderInstance(
instance_id="mock_instance",
gpu_name="RTX_4090",
dph=0.50,
public_ip="127.0.0.1"
)


---

# Deterministic Guarantees

The mock provider must always:

- return the same offers
- return the same instance IDs
- never access network resources
- never depend on environment state

This guarantees stable tests.

---

# Use in Tests

Tests use the mock provider to isolate:

- orchestration logic
- CLI output
- bootstrap script generation
- readiness checks

Example test usage:

```python
provider = MockProvider()

result = run_orchestration(
    provider=provider,
    config=test_config,
    models=["deepseek_llamacpp"]
)
Design Philosophy

The mock provider ensures the system can be tested without:

GPU hardware

cloud infrastructure

network connectivity

This keeps the test suite:

deterministic

fast

reproducible