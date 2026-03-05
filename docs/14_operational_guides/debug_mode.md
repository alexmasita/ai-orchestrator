# docs/14_operational_guides/debug_mode.md

```markdown
# Debug Mode

The system supports runtime diagnostics through the `AI_ORCH_DEBUG` environment variable.

Debug mode enables additional logging during orchestration.

---

# Enabling Debug Mode

Set the environment variable before launching the CLI.

Example:

```bash
AI_ORCH_DEBUG=1 ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper
Debug Logging Behavior

Debug logs are written to stderr.

This preserves the CLI contract that stdout must contain JSON only on success.

Debug Information

When enabled, debug logs include:

Offer Selection

Example:

[debug] selected offer id=12345 gpu=RTX_4090 dph=0.52
Provider Calls

Example:

[debug] VastProvider PUT /asks/12345
Readiness URLs

Example:

[debug] deepseek_url=http://1.2.3.4:8080
[debug] whisper_url=http://1.2.3.4:9000
Readiness Lifecycle

Example:

[debug] waiting for runtime readiness
[debug] runtime ready
Security Constraints

Debug logs must never expose:

API keys

provider tokens

sensitive request payloads

All debug output must be sanitized.

Debug Mode Design Goals

Debug mode was designed to:

diagnose orchestration failures

trace provider interactions

verify runtime readiness behavior

without altering the CLI output contract.