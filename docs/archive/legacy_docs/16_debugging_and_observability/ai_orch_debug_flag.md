AI_ORCH_DEBUG Environment Variable

The environment variable AI_ORCH_DEBUG controls all runtime debug logging.

It enables internal diagnostics across the entire system.

Enabling Debug Mode

Example usage:

AI_ORCH_DEBUG=1 ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper

This activates debug logging across:

orchestrator

provider

runtime healthchecks

Behavior When Disabled

When the variable is not set:

stdout → JSON result
stderr → empty

This ensures CLI output remains stable and script-friendly.

Behavior When Enabled

When enabled:

stdout → JSON result
stderr → debug logs

Example:

[ai-orch] selected offer: RTX_4090
[ai-orch] VastProvider POST /bundles
[ai-orch] waiting for instance readiness
Implementation Contract

Debug mode detection follows:

DEBUG = os.getenv("AI_ORCH_DEBUG") == "1"

Logging helper pattern:

def _debug(msg):
    if DEBUG:
        print(f"[ai-orch] {msg}", file=sys.stderr)
Security Constraints

Debug logging must never expose secrets.

The following must never appear in logs:

Vast API keys

authorization headers

tokens

environment secrets

Only safe diagnostic metadata may be logged.

Test Environment Behavior

All automated tests run with debug mode disabled.

This ensures:

test determinism

predictable output

no unexpected stderr pollution