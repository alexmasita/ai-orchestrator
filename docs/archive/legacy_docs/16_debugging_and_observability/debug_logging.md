Debug Logging Architecture

The ai-orchestrator system implements a strictly controlled debugging system designed to satisfy two critical requirements:

Zero output pollution of CLI JSON results

Deterministic, developer-visible diagnostics

All debugging information is therefore emitted only to stderr and only when debugging is explicitly enabled.

The system avoids traditional logging frameworks intentionally to preserve:

deterministic test behavior

minimal runtime dependencies

predictable output

Logging Output Rules

The following rules govern logging behavior across the entire system.

Rule 1 — CLI stdout must remain pure JSON

When orchestration succeeds:

stdout → JSON only
stderr → nothing

Example success output:

{
  "instance_id": "abc123",
  "gpu_type": "RTX_4090",
  "cost_per_hour": 0.72,
  "idle_timeout": 1800,
  "snapshot_version": "v1",
  "deepseek_url": "http://1.2.3.4:8080",
  "whisper_url": "http://1.2.3.4:9000"
}

Any logging to stdout would break:

automation

scripting

machine parsing

Therefore:

stdout is reserved exclusively for final CLI results.

Rule 2 — Debug information goes to stderr

All debug output is written using:

print(..., file=sys.stderr)

This ensures separation from the CLI result stream.

Rule 3 — Debug logging must be opt-in

Debug logging is only enabled when the environment variable is set:

AI_ORCH_DEBUG=1

If the variable is not set, no debug output is emitted.

Debug Logging Locations

Debug logging is implemented at key orchestration stages.

Orchestrator logging

src/ai_orchestrator/orchestrator.py

Logs:

selected GPU offer

instance creation parameters

readiness checks

readiness success or failure

Example debug output:

[ai-orch] selected offer: id=123 gpu=RTX_4090 dph=0.72
[ai-orch] deepseek_url=http://1.2.3.4:8080
[ai-orch] whisper_url=http://1.2.3.4:9000
[ai-orch] waiting for instance readiness
Provider logging

src/ai_orchestrator/provider/vast.py

Logs:

API endpoints called

HTTP methods used

provider operations

Example:

[ai-orch] VastProvider POST /bundles
[ai-orch] VastProvider PUT /asks/123

Security requirement:

API keys must never be logged.

Runtime readiness logging

src/ai_orchestrator/runtime/healthcheck.py

Logs:

readiness polling attempts

port availability

readiness success

Example:

[ai-orch] checking http://1.2.3.4:8080
[ai-orch] service ready
Logging Design Philosophy

The logging system intentionally avoids:

logging frameworks

configuration files

verbosity levels

Instead it uses a single binary debug switch.

Reasons:

prevents configuration complexity

ensures deterministic test behavior

guarantees no accidental production logging