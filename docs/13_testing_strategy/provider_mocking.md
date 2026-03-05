# Provider Mocking

The `ai-orchestrator` test suite never interacts with the real Vast API.

Provider interactions are mocked to ensure:

- deterministic responses
- no infrastructure side effects
- offline test execution

## Mocking Strategy

Provider tests simulate API behavior using monkeypatched request objects.

Example:


monkeypatch.setattr(vast_module, "requests", fake_requests)


The fake requests object records HTTP calls and returns deterministic responses.

## Simulated API Responses

Tests simulate Vast responses such as:

Offer search:


{
"offers": [
{
"id": "offer123",
"gpu_name": "RTX_4090",
"dph": 0.5
}
]
}


Instance creation:


{
"new_contract": "abc123"
}


Instance details:


{
"instance_id": "abc123",
"gpu_name": "RTX_4090",
"dph": 0.5
}


## Request Recording

Mock request objects record calls.

Example:


calls["put"].append((url, payload))


Tests verify:

- correct endpoint
- correct HTTP method
- deterministic payload

## Network Isolation

All tests must run with:


no external network access


If code attempts to access the real network, tests must fail.

## Error Simulation

Mocks simulate provider failures such as:

- request exceptions
- malformed responses
- HTTP error codes

These tests ensure provider code converts failures into `VastProviderError`.

## Provider Contract Validation

Provider tests ensure:

- correct API endpoints
- correct payload structure
- correct response parsing
- deterministic instance creation