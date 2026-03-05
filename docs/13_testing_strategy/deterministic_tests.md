# Deterministic Tests

Determinism is a core architectural requirement of `ai-orchestrator`.

All tests must behave identically across repeated executions.

## Why Determinism Matters

The orchestrator makes infrastructure decisions based on:

- GPU availability
- pricing
- resource requirements
- configuration

Non-deterministic behavior would produce inconsistent infrastructure deployments.

Therefore the testing system enforces strict determinism.

## Deterministic Test Rules

Tests must not rely on:

- system time
- random number generation
- non-deterministic ordering
- external network responses

Tests must always use fixed inputs.

## Deterministic Output Validation

Many tests verify deterministic outputs.

Examples include:

### CLI JSON Output

CLI output must always be serialized using:


json.dumps(..., sort_keys=True)


Tests verify that identical runs produce identical JSON output.

### Instance Config Generation

The orchestrator generates instance configuration objects.

Tests verify that repeated runs produce identical dictionaries.

### Bootstrap Script Generation

Bootstrap scripts must be deterministic.

The same configuration must produce the same script byte-for-byte.

Tests validate script equality across runs.

## Deterministic Offer Selection

Offer selection must be deterministic.

Given the same inputs:

- provider offers
- resource requirements
- configuration

the selected offer must be identical.

Tests enforce this by running selection multiple times.

## Test Isolation

Every test must be independent.

Tests must not modify global state that persists across runs.

Fixtures reset the environment before execution.

## Deterministic Provider Mocks

Provider responses are simulated using fixed objects.

Example:


{
"id": "offer123",
"gpu_name": "RTX_4090",
"dph": 0.5
}


This ensures orchestration logic behaves predictably.

## Deterministic Execution Guarantee

Running the test suite twice must produce:

- identical pass/fail results
- identical CLI output
- identical orchestration decisions