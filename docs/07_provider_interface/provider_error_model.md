# Provider Error Model

## Purpose

Provider errors represent failures in the infrastructure layer.

These errors must be **normalized and wrapped** before propagating to the CLI.

The goal is to prevent infrastructure libraries from leaking implementation details.

---

# Error Hierarchy


ProviderError
└── VastProviderError


---

# ProviderError

Base class for infrastructure failures.

Example:


ProviderError("Unable to communicate with provider")


---

# VastProviderError

Specialized error for Vast provider failures.

Examples:


VastProviderError("Vast /bundles request failed")
VastProviderError("Invalid response shape from Vast API")
VastProviderError("Instance creation failed")


---

# Wrapping External Exceptions

Providers must wrap external library exceptions.

Example:

Bad:


requests.exceptions.ConnectionError


Correct:


raise VastProviderError("Vast API request failed")


---

# CLI Handling

The CLI converts provider errors into user-facing messages.

Example output:


Provider error: Vast /bundles request failed


Exit code:


1


No stack trace is shown to the user.

---

# Security Constraints

Error messages must not contain:

- API keys
- authentication tokens
- raw HTTP headers
- full request payloads