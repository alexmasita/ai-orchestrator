Runtime Execution Tracing

Runtime tracing allows developers to observe every step of orchestration execution.

Tracing is implemented through debug logs emitted at each critical stage.

Full Execution Trace

The orchestration pipeline follows this sequence:

CLI
  ↓
load_config
  ↓
compute_requirements
  ↓
select_offer
  ↓
provider.search_offers
  ↓
provider.create_instance
  ↓
bootstrap injection
  ↓
wait_for_instance_ready
  ↓
CLI result output

When debug mode is enabled, each step emits trace output.

Example Trace
[ai-orch] loading config
[ai-orch] computing requirements
[ai-orch] searching Vast offers
[ai-orch] selected offer: RTX_4090
[ai-orch] creating instance
[ai-orch] waiting for readiness
[ai-orch] deepseek ready
[ai-orch] whisper ready
Orchestrator Tracing

run_orchestration() traces:

offer selection

instance creation

readiness lifecycle

Example:

[ai-orch] selected offer: id=123 gpu=RTX_4090 dph=0.72
Provider Tracing

Provider tracing logs:

API endpoints

HTTP methods

instance creation operations

Example:

[ai-orch] VastProvider POST /bundles
Runtime Tracing

Runtime readiness tracing logs:

polling attempts

port readiness

HTTP endpoint success

Example:

[ai-orch] checking deepseek readiness
Why Tracing Exists

Tracing enables engineers to diagnose issues such as:

incorrect config values

provider API failures

readiness failures

orchestration logic bugs

Without needing to attach debuggers or instrument code.