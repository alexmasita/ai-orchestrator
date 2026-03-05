# Testing Philosophy

The `ai-orchestrator` project is built around a strict testing philosophy designed to guarantee deterministic infrastructure orchestration.

The testing system exists to ensure that:

- orchestration logic is deterministic
- provider integrations are validated without real infrastructure
- runtime behavior is reproducible
- regressions are detected immediately

The test suite is designed so that a developer can modify internal logic while maintaining system invariants.

## Core Testing Goals

The test system enforces five core guarantees.

### Deterministic Behavior

All tests must produce identical results across repeated runs.

Tests must not rely on:

- system time
- randomness
- network responses
- environment-specific state

This ensures the orchestration engine behaves predictably.

### Infrastructure Isolation

Tests must never interact with real infrastructure.

Specifically:

- no real Vast API calls
- no GPU instance provisioning
- no network dependency

All provider calls are mocked.

### Contract Enforcement

Each system layer has explicit contracts:

CLI → Orchestrator  
Orchestrator → Provider  
Provider → Runtime  
Runtime → Healthchecks  

Tests validate that these contracts remain stable.

### Regression Detection

The system evolved through test-driven changes.

Every architectural change must be validated by tests before implementation.

New functionality must include:

- red tests
- implementation
- passing tests

### Runtime Safety

Runtime code must be validated without running actual GPU instances.

Bootstrap scripts, runtime services, and readiness checks are tested through simulation.

## Test Coverage Philosophy

The system prioritizes testing for:

- orchestration correctness
- provider API handling
- deterministic output
- runtime bootstrapping
- plugin integration

The system intentionally does not test:

- Vast infrastructure behavior
- actual GPU workloads
- network reliability

Those are external concerns.

## Testing Stack

The project uses:

- pytest
- monkeypatch fixtures
- request mocking
- deterministic inputs

All tests run locally without special hardware requirements.

## Test Execution

Tests are executed using:


PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider


This disables bytecode generation and caching to prevent environment-specific artifacts.

## Architectural Testing Guarantee

The entire repository must remain runnable and testable on a machine that has:

- Python
- pytest
- no GPU
- no Vast account

This requirement guarantees portability of the codebase.