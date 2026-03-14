Purpose

The ai-orchestrator system is designed to support multiple infrastructure providers through a strict provider abstraction layer.

Currently implemented:

provider/vast.py

Future providers may include:

AWS EC2

Google Cloud

Azure

Lambda GPU

RunPod

Local GPU clusters

On-prem GPU servers

The provider architecture allows these integrations without modifying orchestration logic.

Provider Layer Architecture

All providers must implement the Provider Interface defined in:

src/ai_orchestrator/provider/interface.py

The required methods:

search_offers(requirements) -> Iterable[ProviderOffer]

create_instance(
    offer_id,
    snapshot_version,
    instance_config
) -> ProviderInstance
ProviderOffer

Represents a candidate GPU resource.

Required fields:

id
gpu_name
vram_gb
dph
reliability
interruptible
ProviderInstance

Represents a launched compute instance.

Required fields:

instance_id
gpu_name
dph
public_ip
Provider Integration Workflow

Provider integration requires implementing:

src/ai_orchestrator/provider/<provider>.py

Example:

provider/aws.py
provider/runpod.py
provider/gcp.py

Each provider must:

Implement search_offers

Implement create_instance

Convert provider-specific API responses into ProviderOffer / ProviderInstance

Deterministic Requirements

Provider implementations must obey the following invariants:

No nondeterministic ordering

Offer lists must preserve the order returned by the provider.

Sorting must be performed only by the orchestrator.

No hidden randomness

Providers must not introduce:

random
timestamps
non-deterministic IDs

in orchestration decisions.

No secrets in logs

Provider debug logging must never expose credentials.

Error Handling

Providers must convert infrastructure failures into:

VastProviderError
ProviderError (future abstraction)

These errors propagate to the CLI layer, which converts them into:

Provider error: <message>
Testing Requirements

Provider implementations must support full test mocking.

Tests must:

monkeypatch requests

avoid network calls

produce deterministic responses