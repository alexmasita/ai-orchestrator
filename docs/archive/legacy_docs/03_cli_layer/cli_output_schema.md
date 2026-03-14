# CLI Output Schema

This document defines the user-facing JSON schema printed by the CLI on success.

The schema is intentionally small and stable. On success, stdout must contain exactly one line of JSON.

---

## Success Output (stdout)

### Contract

- Output is **a single JSON line**.
- Serialization is deterministic: `json.dumps(..., sort_keys=True)`.
- The schema is stable across versions unless explicitly versioned.

### Schema

```json
{
  "instance_id": "string",
  "gpu_type": "string",
  "cost_per_hour": "number",
  "idle_timeout": "number",
  "snapshot_version": "string",
  "deepseek_url": "string",
  "whisper_url": "string"
}
Field Semantics
instance_id (string)

Provider instance identifier.

Originates from orchestration/provider.

gpu_type (string)

Public GPU identity shown to user.

Compatibility mapping rule:

prefer raw_result["gpu_type"]

fallback to raw_result["gpu_name"]

Examples:

"RTX_4090"

"A100"

"RTX_A6000"

cost_per_hour (number)

The hourly price for the instance (dollars per hour).

Compatibility mapping rule:

prefer raw_result["cost_per_hour"]

fallback to raw_result["dph"]

idle_timeout (number)

Idle timeout value used by the orchestrator/provider lifecycle, if present in orchestration return payload.

This is distinct from idle_timeout_seconds used internally for provider configuration injection.

The CLI treats it as a reported value and does not compute it.

snapshot_version (string)

Snapshot version propagated from configuration and orchestration.

Used to ensure deterministic snapshot selection across runs.

deepseek_url (string)

URL where DeepSeek service is expected to be reachable.

Usually computed using provider instance IP + fixed port 8080.

Fallback rule (only if orchestration does not supply a URL):

"http://127.0.0.1:8080"

whisper_url (string)

URL where Whisper service is expected to be reachable.

Usually computed using provider instance IP + fixed port 9000.

Fallback rule (only if orchestration does not supply a URL):

"http://127.0.0.1:9000"

Explicit Exclusions

The CLI output must not leak provider internal keys. In particular, the CLI must not print:

gpu_name

dph

raw provider API payloads

Vast offer structures

secrets (API keys, tokens)

Any internal debugging must go to stderr under AI_ORCH_DEBUG=1.

Failure Output (stderr)

On failure, the CLI should print one-line stderr messages for known error types:

Configuration problems:

Configuration error: <message>

Provider problems:

Provider error: <message>

The CLI should return exit code 1 on failures.


---

If you want, I can do the next docs batch in the same “drop-in file” format (e.g., `04_orchestrator_core/*` or `08_vast_provider/*`).