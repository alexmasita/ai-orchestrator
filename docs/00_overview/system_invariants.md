System Invariants

System invariants are rules that must never be violated.

Violating these invariants risks breaking the system architecture.

CLI Output Must Be JSON

On success, the CLI must print only JSON to stdout.

No additional text may be printed.

Example:

{
  "instance_id": "abc123",
  "gpu_type": "RTX_4090"
}

Debug messages must go to stderr.

Provider Layer Must Not Leak Secrets

Provider logs must never expose:

API keys

authentication tokens

credentials

Tests Must Not Use Real Network

All tests must run without network access.

Provider tests use mocked HTTP requests.

Bootstrap Script Must Be Deterministic

Bootstrap script generation must always produce identical output for identical inputs.

This ensures reproducibility.

Runtime Ports Are Fixed

Service ports must remain fixed:

DeepSeek → 8080
Whisper → 9000

Changing ports would break readiness checks and CLI output contracts.

Provider Response Parsing Must Be Explicit

Provider implementations must validate response schemas.

Unexpected response shapes must produce errors.

Orchestrator Must Remain Stateless

The orchestrator must not maintain persistent internal state.

Each invocation must be independent.