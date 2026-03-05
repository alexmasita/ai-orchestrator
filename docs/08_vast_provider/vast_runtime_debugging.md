Purpose

This document explains how to diagnose Vast runtime issues.

Debug Mode

Enable debugging:

AI_ORCH_DEBUG=1

Example:

AI_ORCH_DEBUG=1 ai-orchestrator start ...
Debug Logs

Debug output includes:

selected offer id
gpu type
cost per hour
constructed runtime URLs
readiness checks

Example:

[orch] selected offer id=123 gpu=RTX_4090 dph=0.72
[orch] readiness deepseek=http://1.2.3.4:8080
Common Failures
DNS Failure

Example:

Failed to resolve console.vast.ai

Fix:

nslookup console.vast.ai
Missing requests Dependency

Error:

Provider error: requests dependency is missing

Fix:

pip install -e .
Invalid API URL

If quotes remain in config:

"https://console.vast.ai/api/v0"

Normalization strips quotes automatically.

Invalid API Response

Error:

Unexpected /bundles response shape

Cause:

Vast API response format changed.

Diagnosing Instance Failures

Steps:

verify instance creation succeeded

verify ports exposed

verify runtime bootstrap executed

verify readiness checks passed

End of Vast Provider Architecture Docs

These documents precisely capture:

Vast provider responsibilities

API integration

request/response contracts

runtime bootstrap injection

provider error handling

debugging procedures