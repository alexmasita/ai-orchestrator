Diagnosing Provider Failures

Provider failures are the most common runtime issues when interacting with Vast infrastructure.

The system isolates provider errors using the VastProviderError exception.

Provider Failure Categories

Provider failures typically fall into these categories:

1 — Network connectivity failures

Example:

Provider error: Vast /bundles request failed: Failed to resolve console.vast.ai

Cause:

DNS issues

no internet connectivity

firewall restrictions

Diagnosis:

nslookup console.vast.ai
curl https://console.vast.ai
2 — Invalid API key

Example:

Provider error: Vast authentication failed

Cause:

incorrect vast_api_key

Fix:

Update config.yaml.

3 — Invalid request payload

Example:

Provider error: Vast /bundles returned unexpected response

Cause:

API schema changes

provider integration bug

Diagnosis:

Enable debug mode:

AI_ORCH_DEBUG=1 ai-orchestrator start ...

Inspect provider requests.

4 — Instance creation failure

Example:

Provider error: Vast instance creation failed

Possible causes:

insufficient GPU availability

account limits

incorrect offer ID

Debugging Provider Calls

Enable debug mode:

AI_ORCH_DEBUG=1 ai-orchestrator start ...

Observe provider logs:

[ai-orch] VastProvider POST /bundles
[ai-orch] VastProvider PUT /asks/123
Error Wrapping Contract

All HTTP failures are wrapped into:

VastProviderError

This ensures:

CLI shows a clean one-line error

stack traces are avoided for users

Example output:

Provider error: Vast /bundles request failed: connection timeout
Provider Debugging Checklist

When debugging provider failures:

Verify network connectivity

curl https://console.vast.ai/api/v0/bundles

Verify API key

Enable debug logs

AI_ORCH_DEBUG=1

Inspect provider endpoint calls

Verify response parsing assumptions

Future Provider Observability Improvements

Potential improvements:

structured debug logging

request/response tracing

retry metrics

provider health checks

These are intentionally deferred to maintain the current system's minimal deterministic architecture.