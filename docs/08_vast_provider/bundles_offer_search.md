Purpose

The Vast provider discovers available GPU offers through the Vast API.

The orchestrator then selects the best offer.

Endpoint
POST /bundles

Example endpoint:

https://console.vast.ai/api/v0/bundles
Request Structure

The provider builds a deterministic search payload.

Example request body:

{
  "gpu_ram": 24,
  "reliability": 0.98,
  "verified": true,
  "limit": 50
}

Filters come from:

config.yaml

Examples:

Field	Meaning
gpu_ram	minimum VRAM requirement
reliability	minimum reliability
verified	require verified hosts
Deterministic Payload Generation

The request payload must be deterministic.

Rules:

consistent key ordering

no random parameters

identical config → identical payload

Response Structure

Typical Vast response:

{
  "offers": [
    {
      "ask_contract_id": "12345",
      "gpu_name": "RTX_4090",
      "dph_total": 0.72,
      "gpu_ram": 24,
      "reliability2": 0.99
    }
  ]
}
Supported Response Shapes

The provider supports two shapes:

Wrapped response
{ "offers": [...] }
Raw list
[ ... ]

If the response does not match either shape:

VastProviderError("Unexpected /bundles response shape")
Offer Normalization

Each offer is converted to:

ProviderOffer

Mapping:

Vast Field	Provider Field
ask_contract_id	id
gpu_name	gpu_name
gpu_ram	vram_gb
dph_total	dph
reliability2	reliability
Offer Order

Offers must preserve the exact order returned by the API.

Sorting is performed only by the orchestrator, not the provider.