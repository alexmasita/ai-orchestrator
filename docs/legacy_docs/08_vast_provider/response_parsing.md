Purpose

The Vast provider converts API responses into provider-agnostic objects.

Parsing Goals

Response parsing must:

tolerate minor API variations

reject malformed responses

remain deterministic

Offer Parsing

Fields used:

ask_contract_id
gpu_name
gpu_ram
dph_total
reliability2

Fallbacks are allowed.

Example:

dph_total → dph
reliability2 → reliability
Instance Parsing

Fields extracted:

instance_id
gpu_name
dph_total
public_ipaddr

Fallbacks:

dph_total → dph
Validation Rules

Invalid responses raise:

VastProviderError

Examples:

missing contract id

missing GPU name

invalid JSON structure