Configuration Field Reference

This document defines every supported configuration field, its type, default behavior, and usage.

Provider Settings
vast_api_key

Type

string

Description

Vast.ai API key used for authentication.

Example

vast_api_key: "abcdef123"

Security rules

Must never be logged

Must never appear in debug output

vast_api_url

Type

string

Example

vast_api_url: "https://console.vast.ai/api/v0"

Purpose

Defines the base URL used by the Vast provider client.

Used to build endpoints:

/bundles
/asks/{id}
/instances/{id}

Normalization rules apply (see normalization document).

GPU Selection
gpu.min_vram_gb

Type

integer

Example

gpu:
  min_vram_gb: 24

Purpose

Minimum VRAM required for the selected models.

Offers with less VRAM are rejected.

gpu.preferred_models

Type

list[string]

Example

preferred_models:
  - RTX_4090
  - RTX_A6000
  - A100

Purpose

Defines preferred GPU types.

Used as ranking hints during offer selection.

Network Requirements
min_inet_down_mbps

Type

integer

Example

min_inet_down_mbps: 100

Purpose

Minimum download speed required.

Offers below this threshold are filtered out.

min_inet_up_mbps

Type

integer

Example

min_inet_up_mbps: 100

Purpose

Minimum upload speed.

Reliability Filters
reliability_min

Type

float

Example

reliability_min: 0.98

Purpose

Minimum host reliability score.

verified_only

Type

boolean

Example

verified_only: true

Purpose

If enabled:

Only verified hosts are considered.

Pricing Constraints
max_dph

Type

float

Example

max_dph: 0.6

Meaning

Maximum allowed cost per hour.

Offers exceeding this value are rejected.

allow_interruptible

Type

boolean

Example

allow_interruptible: true

Purpose

Determines whether interruptible instances are allowed.

Model Requirements
whisper_vram_gb

Type

integer

Example

whisper_vram_gb: 8

Purpose

VRAM required for Whisper runtime.

Required if whisper model is enabled.

whisper_disk_gb

Type

integer

Example

whisper_disk_gb: 10

Purpose

Disk storage required for Whisper runtime.

Runtime Configuration
idle_timeout_seconds

Type

integer

Example

idle_timeout_seconds: 1800

Rules

Must be a positive integer

Invalid values raise ValueError

Purpose

Determines idle shutdown timeout.

snapshot_version

Type

string

Example

snapshot_version: "v1"

Purpose

Used by provider snapshot logic.