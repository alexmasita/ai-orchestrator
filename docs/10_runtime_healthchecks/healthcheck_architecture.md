# Runtime Healthchecks Architecture

This system performs **runtime readiness checks** after a provider instance is created, and before the orchestration result is returned to the CLI as "ready".

Healthchecks are implemented in:

- `src/ai_orchestrator/runtime/healthcheck.py`

and are invoked from:

- `src/ai_orchestrator/orchestrator.py` (inside `run_orchestration(...)`)

## Goals

Healthchecks exist to ensure:

1. The instance is reachable (network path is up).
2. The service ports are listening.
3. The HTTP endpoints respond successfully.
4. The orchestrator returns only once the runtime is actually usable.

## Non-Goals

Healthchecks do **not**:

- provision the instance (that is provider responsibility)
- install dependencies or models (that is bootstrap responsibility)
- implement retries for provider API operations (provider layer responsibility)
- return partial success (either ready or fail)

## Components

The healthcheck layer is built around three functions:

### 1) `wait_for_port(...)`

A TCP probe that repeatedly attempts to connect to a target host/port until success or timeout.

- Returns `True` on success.
- Raises `RuntimeError` on timeout.

### 2) `wait_for_http(...)`

An HTTP GET probe that repeatedly hits a URL until it returns HTTP 200 or timeout.

- Returns `True` on success.
- Raises `RuntimeError` on timeout.

### 3) `wait_for_instance_ready(...)`

The orchestrator-level readiness gate.

It orchestrates the checks needed for the deployed services. The current design assumes:

- DeepSeek service is reachable at port **8080**
- Whisper service is reachable at port **9000**

and that readiness includes port checks and HTTP 200 checks.

It:

- performs DeepSeek port + HTTP checks
- performs Whisper port + HTTP checks
- returns `True` if all pass
- raises `RuntimeError` if any check fails or times out

## Invocation Point (Orchestrator)

Readiness checks are performed after:

- `select_offer(...)`
- `provider.create_instance(...)`

and before the final result is returned.

The orchestrator resolves the IP used for readiness in priority order:

1. `instance.public_ip`
2. `instance.ip`
3. fallback `"127.0.0.1"`

Then constructs deterministic URLs:

- `deepseek_url = f"http://{ip}:8080"`
- `whisper_url = f"http://{ip}:9000"`

Then calls:

- `wait_for_instance_ready(ip, deepseek_url=..., whisper_url=...)`

### Readiness Call Ordering Invariant

The readiness call must occur **after** instance creation and **before** returning orchestration output.

This is enforced by tests (call ordering is deterministic and asserted).

## Determinism Guarantees

Healthcheck behavior is deterministic in the following senses:

- URL construction is deterministic (fixed ports, deterministic IP selection)
- retry loops are time-based using monotonic time (not wall clock)
- exceptions are not swallowed; failure propagates consistently
- orchestration calls readiness exactly once per invocation

The only nondeterminism comes from the real world (network timing, remote boot time).

## Output / Observability

The readiness layer does not alter CLI output schema. It only gates success.

Optional debug logging may exist upstream (orchestrator-level) but healthcheck functions themselves are contract-driven:

- return `True` on success
- raise `RuntimeError` on failure