# User-Facing Errors

This document describes how the system presents errors to end users.

The CLI must always produce **clean, readable messages**.

---

# CLI Error Output Rules

The CLI follows strict rules:

| Rule | Description |
|----|----|
| stdout | reserved for JSON success output |
| stderr | used for errors |
| no traceback | user never sees stack traces |
| deterministic | identical failures produce identical messages |

---

# Example CLI Failure Output

Example configuration error:


Configuration error: Missing whisper config


---

Example provider failure:


Provider error: Vast /bundles request failed


---

Example orchestration failure:


Orchestration error: instance readiness failed


---

# Exit Codes

| Exit Code | Meaning |
|------|------|
| 0 | success |
| 1 | failure |

---

# Debug Mode

When debug mode is enabled:


AI_ORCH_DEBUG=1


The system prints additional diagnostic logs.

Example:


[DEBUG] selected offer: RTX_4090
[DEBUG] readiness check starting


These logs go to:


stderr


---

# JSON Success Output

On success the CLI prints JSON only.

Example:

```json
{
  "instance_id": "abc123",
  "gpu_type": "RTX_4090",
  "cost_per_hour": 0.72,
  "deepseek_url": "http://1.2.3.4:8080",
  "whisper_url": "http://1.2.3.4:9000"
}
UX Design Philosophy

The CLI follows these UX rules:

Errors should be actionable

Errors should be short

Errors should not leak internal details

Debugging details appear only in debug mode

Summary

User-facing errors are designed to ensure:

operational clarity

deterministic behavior

safe error reporting

easy debugging without exposing internals