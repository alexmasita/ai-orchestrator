# HTTP Readiness Checks

HTTP readiness checks validate that a service is not just listening, but responding successfully at its HTTP endpoint.

This is implemented by:

- `ai_orchestrator.runtime.healthcheck.wait_for_http(...)`

## Contract

`wait_for_http(...)`:

- repeatedly performs an HTTP request (typically GET) to a URL
- retries until it sees an HTTP 200 response or the timeout is exceeded
- returns `True` when HTTP 200 is observed
- raises `RuntimeError` when the timeout is exceeded

### Success Definition

A service is considered HTTP-ready when:

- the endpoint responds with **HTTP 200**

Other HTTP status codes are treated as “not ready yet” (or failing), depending on the implementation, but the contract enforced in this project is:

- readiness requires HTTP 200

### Failure Definition

HTTP readiness fails when:

- the service never returns HTTP 200 within the timeout
- the port is not reachable
- connection fails repeatedly
- the service returns persistent non-200 codes (misconfigured, crashing, wrong route)

## Relationship to Port Readiness

Port readiness and HTTP readiness cover different failure modes:

- port check: “is something listening?”
- HTTP check: “is the correct service responding successfully?”

The canonical readiness flow checks ports first, then HTTP.

## URLs Used by ai-orchestrator

The orchestrator constructs deterministic service base URLs:

- `deepseek_url = http://{ip}:8080`
- `whisper_url = http://{ip}:9000`

Those URLs are included in the orchestration output and surfaced via CLI.

The healthcheck layer uses these same URLs (or derived endpoint URLs) so that:

- the readiness criteria match what the user will actually call
- returned URLs are guaranteed usable on success

## Security and Secrets

HTTP readiness checks do not include authentication headers by design.
They are intended for local service readiness endpoints.

If future services require auth, the readiness contract must be revisited with explicit support for headers/tokens.