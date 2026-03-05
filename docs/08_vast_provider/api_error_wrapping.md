Purpose

The Vast provider converts HTTP failures into structured provider errors.

Error Type
VastProviderError

This error type is used exclusively for provider failures.

Request Failures

Network exceptions:

ConnectionError
Timeout
InvalidSchema

Are wrapped as:

VastProviderError("Vast API request failed")
HTTP Errors

If the API returns non-200 status:

HTTP 4xx
HTTP 5xx

The provider raises:

VastProviderError("Vast API returned status <code>")
Security Rule

Errors must never expose:

API keys
Authorization headers
internal request payloads
CLI Behavior

The CLI converts provider errors to user messages:

Provider error: <message>

Exit code:

1