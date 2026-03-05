# Data Flow Contracts

This document describes the data structures that move between system layers.

Strict contracts ensure architectural stability and prevent implicit coupling.

---

# Core Data Objects

The orchestration pipeline uses several internal objects.


Config
SizingInput
SizingResult
ProviderOffer
ProviderInstance
CLIOutput


Each structure has explicit field definitions.

---

# Config Object

Produced by:


load_config()


Example structure:


{
"vast_api_key": "...",
"vast_api_url": "...",
"max_dph": 0.6,
"idle_timeout_seconds": 1800,
"gpu": {
"min_vram_gb": 24
}
}


The configuration object is treated as immutable after loading.

---

# SizingInput

Constructed by the CLI.


SizingInput:
models: List[str]
config: Dict


Purpose:

Define the model set and configuration used by the sizing engine.

---

# SizingResult

Output of the sizing engine.


SizingResult:
required_vram_gb
required_disk_gb
required_inet_down
required_inet_up


This result drives provider offer filtering.

---

# ProviderOffer

Represents an infrastructure offer.


ProviderOffer:
id: str
gpu_name: str
dph: float
reliability: float
interruptible: bool


These objects are produced by:


provider.search_offers()


Provider-specific responses are normalized into this format.

---

# ProviderInstance

Represents a running instance.


ProviderInstance:
instance_id: str
gpu_name: str
dph: float
public_ip: Optional[str]


Produced by:


provider.create_instance()


---

# Instance Config

Passed to the provider during creation.


{
bootstrap_script: str,
idle_timeout_seconds: int
}


Bootstrap scripts must remain deterministic.

---

# CLI Output Contract

The CLI outputs a strict JSON schema.


{
instance_id
gpu_type
cost_per_hour
idle_timeout
snapshot_version
deepseek_url
whisper_url
}


Provider-specific fields must never leak into CLI output.

---

# Contract Stability

These contracts must remain stable across versions.

Breaking changes must include:

• migration strategy  
• version bump  
• documentation updates