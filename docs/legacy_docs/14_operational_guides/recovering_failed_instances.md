# Recovering Failed Instances

In some cases an instance may be created successfully but fail during runtime startup.

This document explains how to recover from such situations.

---

# Failure Scenario

Example:

- instance created
- bootstrap script fails
- readiness check fails

The orchestrator exits but the instance remains running.

---

# Identifying the Instance

The CLI prints the instance ID.

Example:


"instance_id": "abc123"


Use this ID to inspect the instance in the provider dashboard.

---

# Manual Inspection

Log into the provider control panel and inspect:

- container logs
- system logs
- runtime services

Check if:

- bootstrap script executed
- ports are open
- runtime containers started

---

# Manual Termination

If the instance is unusable it should be terminated manually.

Steps:

1. locate the instance in the provider console
2. terminate the instance

This avoids unnecessary billing.

---

# Restart Strategy

After termination, fix the root cause and relaunch the system:

```bash
ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper
Common Recovery Fixes

Typical fixes include:

correcting configuration values

fixing bootstrap script logic

adjusting GPU requirements

increasing network limits

Long-Term Mitigation

Future system extensions may include:

automatic instance cleanup

retry orchestration

bootstrap failure detection

instance reuse pools