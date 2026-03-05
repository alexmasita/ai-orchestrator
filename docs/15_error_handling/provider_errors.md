# Provider Errors

Provider errors occur when communication with a cloud provider fails.

In the current implementation, the only supported provider is:


Vast.ai


All provider failures must be converted into:


VastProviderError


---

# Provider Error Class

Defined in:


src/ai_orchestrator/provider/vast.py

class VastProviderError(Exception)


This error represents failures interacting with the Vast API.

---

# Provider Error Sources

Provider errors can originate from:

| Source | Example |
|------|------|
| network failure | DNS resolution failure |
| invalid API response | malformed JSON |
| missing response fields | missing `new_contract` |
| HTTP error | 401 / 403 / 500 |
| unexpected response structure | incorrect bundles payload |

---

# API Request Failure

Example failure:


requests.exceptions.RequestException


This is wrapped as:


VastProviderError("Vast /bundles request failed")


---

# Example Failure Message


Provider error: Vast /bundles request failed: DNS resolution failed


---

# Response Shape Validation

Provider responses must match expected structure.

Example expected:


{
"offers": [...]
}


If the response shape is invalid:


VastProviderError("Unexpected /bundles response shape")


---

# Instance Creation Failure

Instance creation requires:


PUT /asks/{offer_id}


Expected response:


{
"new_contract": <instance_id>
}


Missing field produces:


VastProviderError("Instance creation response missing new_contract")


---

# Instance Lookup Failure

After creation, the system performs:


GET /instances/{id}


Failures are wrapped as provider errors.

---

# CLI Handling

The CLI handles provider errors with:

```python
except VastProviderError as exc:
    print(f"Provider error: {exc}", file=sys.stderr)
    return 1

Result:

Provider error: Vast /bundles request failed
Security Rules

Provider errors must never expose:

API keys

Authorization headers

secrets

All error messages must be sanitized.

Summary

Provider errors represent infrastructure failures.

They ensure:

network errors do not crash the CLI

provider failures produce deterministic output

secrets are never leaked