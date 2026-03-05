# Failure Handling

The healthcheck layer uses a strict failure model:

- success is `True`
- failure is an exception (`RuntimeError`)

There is no partial readiness.

## Failure Propagation Rules

### Inside healthcheck functions

- `wait_for_port(...)` raises `RuntimeError` on timeout
- `wait_for_http(...)` raises `RuntimeError` on timeout
- `wait_for_instance_ready(...)` raises `RuntimeError` if any required check fails

These exceptions are **not** converted into other error types inside the healthcheck module.

### In orchestrator

`run_orchestration(...)` does not swallow readiness failures.

If `wait_for_instance_ready(...)` raises `RuntimeError`, orchestration fails and the exception propagates upward.

This behavior is intentional and tested:

- tests assert that readiness failures propagate as `RuntimeError`

## Why RuntimeError?

The readiness layer uses `RuntimeError` as a clear signal that:

- infrastructure provisioning succeeded
- but runtime services did not become ready within constraints

Higher layers can optionally catch this and present a cleaner UX, but the core contract is:

- readiness failures are hard failures

## Cleanup Responsibility

Healthcheck failures do not automatically terminate instances.

Cleanup is explicitly a provider/orchestrator policy decision.

Future work may introduce:

- optional cleanup-on-failure flags
- provider termination calls on readiness failure
- quarantine / retry policies

For now, the invariant is:

- readiness failure does not imply automatic deletion
- the error propagates so the operator can decide what to do

## Debugging Failures

When a readiness failure occurs, common causes include:

- bootstrap script failed (dependencies missing, build errors)
- model download stalled or failed
- service process crashed
- ports not exposed / wrong port mapping
- firewall rules / provider networking not opening the port
- wrong bind address (must bind to 0.0.0.0 for remote access)

Recommended steps:

1. enable debug logging (if supported upstream) such as `AI_ORCH_DEBUG=1`
2. inspect provider instance logs (Vast onstart logs / container logs)
3. verify the bootstrap script content injected into provider
4. verify expected ports are mapped and listening
5. manually curl the endpoints from a reachable network location

## Contract Preservation During Failures

Even in failure cases, these invariants must hold:

- no secrets printed to stdout
- CLI success output must remain JSON-only
- failure paths should prefer one-line stderr messages (where implemented)
- deterministic ordering and call count remain stable (no extra hidden retries outside healthcheck loops)