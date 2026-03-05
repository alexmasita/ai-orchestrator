# Port Readiness Checks

Port readiness checks verify that a service has opened a listening socket and is accepting TCP connections.

This is implemented by:

- `ai_orchestrator.runtime.healthcheck.wait_for_port(...)`

## Contract

`wait_for_port(...)`:

- attempts to connect to a target `(host, port)`
- retries until success or timeout
- returns `True` when a connection succeeds
- raises `RuntimeError` when the timeout is exceeded

### Failure Definition

Port readiness fails when:

- the service process has not started
- the port is not bound yet
- the service crashed
- network routing/firewall blocks the connection
- the remote host is unreachable

### Success Definition

Port readiness succeeds as soon as:

- a TCP connection can be established to the target port

Port readiness does **not** validate that the service is “healthy” or “correct”—only that something is listening.

## Retry Loop Model

The retry loop is based on `time.monotonic()` (monotonic time), not wall-clock time.

This prevents failures due to clock skew or NTP adjustments and ensures:

- stable timeout behavior
- deterministic timeout calculation

Typical loop behavior:

1. compute deadline based on monotonic start + timeout
2. attempt to connect
3. on failure, sleep briefly (or immediately retry)
4. if deadline exceeded, raise `RuntimeError`

The exact retry interval is an implementation detail, but the monotonic-deadline model is part of the contract.

## Ports Used by ai-orchestrator

The runtime architecture assumes fixed service ports:

- DeepSeek: **8080**
- Whisper: **9000**

These are treated as stable invariants across:

- bootstrap script generation
- orchestrator URL construction
- readiness checks
- CLI output defaults

If ports change in future, they must change across all these layers together.

## Usage in Instance Readiness

Port checks are orchestrated by `wait_for_instance_ready(...)` and typically occur before HTTP checks.

Reason: HTTP checks are noisy if the port is not open yet; port checks provide an earlier, simpler readiness gate.