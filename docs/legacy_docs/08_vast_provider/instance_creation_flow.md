Purpose

The instance creation flow provisions a GPU instance using a selected offer.

Step 1 — Bootstrap Injection

The orchestrator generates a bootstrap script.

The provider injects the script into the Vast request.

instance_config["bootstrap_script"]
Step 2 — Instance Creation Request

Endpoint:

PUT /asks/{offer_id}

Example:

PUT https://console.vast.ai/api/v0/asks/12345

Payload:

{
  "image": "ubuntu:22.04",
  "runtype": "ssh_direct",
  "onstart": "<bootstrap_script>",
  "env": {
    "-p 8080:8080": "1",
    "-p 9000:9000": "1"
  }
}
Ports

The bootstrap environment exposes two ports:

Port	Service
8080	DeepSeek API
9000	Whisper API

These ports must always be exposed.

Step 3 — Instance Contract ID

The creation response returns:

new_contract

Example:

{
  "new_contract": "abc123"
}
Step 4 — Instance Lookup

After creation, the provider queries instance details.

GET /instances/{contract_id}

This retrieves:

public_ipaddr
gpu_name
dph_total
Step 5 — ProviderInstance

The provider returns:

ProviderInstance(
  instance_id,
  gpu_name,
  dph,
  public_ip
)