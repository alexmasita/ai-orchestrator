Purpose

The Vast Provider layer implements the infrastructure provider integration used by the orchestrator to acquire GPU compute instances.

It translates the provider-agnostic orchestration contract into Vast.ai API operations.

This layer is responsible for:

discovering available GPU offers

filtering and returning provider offers

creating instances from selected offers

returning normalized provider objects to the orchestrator

handling API failures safely

isolating the rest of the system from provider-specific behavior

The orchestrator never interacts with the Vast API directly.

All Vast logic lives exclusively inside:

src/ai_orchestrator/provider/vast.py
Architectural Role

The Vast provider implements the Provider Interface contract defined in:

src/ai_orchestrator/provider/interface.py

This ensures the orchestrator can support multiple providers in the future.

Orchestrator
     ↓
Provider Interface
     ↓
VastProvider
     ↓
Vast API
Responsibilities

The Vast provider performs the following responsibilities:

1. Offer Discovery

Search Vast marketplace offers that satisfy orchestration requirements.

search_offers(requirements)

Returns normalized ProviderOffer objects.

2. Instance Creation

Provision a new GPU instance from a selected offer.

create_instance(offer_id, snapshot_version, instance_config)

This injects the bootstrap script and starts the runtime.

3. Instance Normalization

Convert Vast API responses into provider-agnostic objects:

ProviderOffer
ProviderInstance

These are consumed by the orchestrator.

4. Error Normalization

Convert all Vast API failures into:

VastProviderError

This ensures the CLI receives clean user-visible errors instead of raw stack traces.

VastProvider Object

Constructor:

VastProvider(
    api_key: str,
    base_url: str
)

Parameters:

Parameter	Purpose
api_key	Vast API authentication
base_url	Vast API endpoint

Example:

https://console.vast.ai/api/v0

The base URL is normalized internally.

Internal Components

The provider internally implements:

Component	Responsibility
HTTP request helpers	Perform Vast API calls
response parser	Convert raw API responses
error wrapper	Convert request errors
endpoint builder	Construct deterministic API URLs
Provider Data Models
ProviderOffer

Represents a marketplace offer.

Fields:

id
gpu_name
vram_gb
dph
reliability
interruptible
ProviderInstance

Represents a running instance.

Fields:

instance_id
gpu_name
dph
public_ip

public_ip is used by the orchestrator to build runtime URLs.

Deterministic Behavior

Provider logic must remain deterministic:

identical inputs → identical payloads

API responses must not reorder offers

provider must not introduce randomness

Security Constraints

The provider must never expose secrets.

Forbidden outputs:

API keys
Authorization headers
provider request payloads containing secrets

Debug logs must never print secrets.

Provider Isolation

The rest of the system must not depend on Vast-specific behavior.

This enables future providers such as:

AWS

GCP

RunPod

Lambda Labs