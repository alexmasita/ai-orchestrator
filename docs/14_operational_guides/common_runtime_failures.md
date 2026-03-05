# Common Runtime Failures

This document describes common runtime failures encountered during orchestration and how to resolve them.

---

# 1. Configuration Errors

Example error:


Configuration error: Missing whisper config


Cause:

Required configuration fields are missing when running Whisper.

Required fields:


whisper_vram_gb
whisper_disk_gb


Fix:

Add them to `config.yaml`.

---

# 2. Provider Network Failures

Example:


Provider error: Vast /bundles request failed: DNS resolution error


Cause:

Network connectivity issues.

Possible causes:

- DNS failure
- firewall restrictions
- VPN interference

Fix:

Verify connectivity:


curl https://console.vast.ai


---

# 3. Missing Dependencies

Example:


Provider error: requests dependency is missing


Cause:

Python dependency not installed.

Fix:


pip install -e .


---

# 4. Invalid Provider API Responses

Example:


Unexpected /bundles response shape


Cause:

Provider API response format changed.

Fix:

Inspect provider API response using debug mode.

---

# 5. Instance Readiness Timeout

Example:


RuntimeError: instance not ready


Cause:

Runtime services failed to start.

Possible reasons:

- bootstrap script failure
- runtime container crash
- network ports not exposed

Fix:

Inspect instance logs via provider dashboard.

---

# 6. Invalid Configuration URL

Example:


InvalidSchema: No connection adapters found


Cause:

Quoted URLs in configuration.

Example incorrect value:


"https://console.vast.ai/api/v0
"


Fix:

Remove extra quotes or rely on config normalization.

---

# Failure Diagnosis Strategy

When failures occur:

1. Enable debug mode
2. Inspect provider responses
3. Verify configuration values
4. Confirm network connectivity
5. Check runtime container logs