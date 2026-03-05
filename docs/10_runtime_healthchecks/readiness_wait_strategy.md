# Readiness Wait Strategy

Readiness waiting is implemented as a set of deterministic retry loops:

- `wait_for_port(...)` retry loop for TCP connect
- `wait_for_http(...)` retry loop for HTTP 200
- `wait_for_instance_ready(...)` sequencing logic across services

## Design Requirements

The waiting strategy must:

1. avoid wall-clock time dependency (use monotonic time)
2. provide a clear timeout failure signal (raise)
3. return immediately upon success
4. be deterministic in ordering and invocation count (tests depend on this)
5. not mutate global state
6. not sleep for unbounded time

## Time Base: `time.monotonic()`

All timeouts are computed using `time.monotonic()` rather than `time.time()`.

This ensures timeout behavior does not drift due to:

- system time adjustments
- NTP corrections
- leap seconds / clock skew

## Deterministic Ordering

Within one orchestration invocation, the readiness orchestration is deterministic:

- instance is created
- IP is resolved deterministically
- DeepSeek checks occur
- Whisper checks occur
- return success only after both pass

Tests explicitly enforce:

- readiness is called exactly once per orchestration run
- readiness is called after provider.create_instance
- repeated runs with identical inputs produce identical call sequences and URL args

## Retry Interval Guidance

The retry interval is intentionally an implementation detail, but system behavior must meet:

- multiple attempts within the timeout window
- no busy-looping that burns CPU
- no overly slow polling that delays readiness unnecessarily

In practice, a short sleep (e.g., a few hundred milliseconds) between retries is typical.

## Timeout and Thresholds

Timeouts are enforced by raising `RuntimeError`.

The exact default timeout values are implementation details and may evolve, but invariants remain:

- success returns `True`
- timeout raises `RuntimeError`
- exceptions are not swallowed

## Orchestrator Responsibility vs Healthcheck Responsibility

- healthcheck layer: "is this instance and its services ready?"
- orchestrator layer: "when do we call readiness, and what URLs do we publish?"

The orchestrator must not bypass readiness for provider flows that claim remote endpoints, because that breaks the meaning of "start succeeded".

If readiness is skipped in future (e.g., certain run modes), it must be explicit and documented as a different orchestration contract.