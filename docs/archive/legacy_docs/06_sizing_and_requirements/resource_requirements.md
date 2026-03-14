Purpose

This document defines the resource requirement model used by the orchestrator.

Resource requirements describe the minimum infrastructure capability needed to run requested models.

These requirements are computed before any provider interaction.

Resource Categories

The system tracks four primary resource dimensions:

Resource	Description
GPU VRAM	GPU memory required for models
Disk	local storage required for artifacts
Network Down	required download bandwidth
Network Up	required upload bandwidth
GPU VRAM

GPU VRAM determines which GPUs can run the models.

Example GPUs:

GPU	VRAM
RTX 3090	24GB
RTX 4090	24GB
A100	40GB / 80GB

The orchestrator filters provider offers using VRAM.

Disk Requirements

Disk requirements include:

model weights

runtime binaries

inference cache

temporary files

Disk requirements accumulate across models.

Network Requirements

Network constraints are configured by the user.

Example:

min_inet_down_mbps: 100
min_inet_up_mbps: 100

These constraints filter provider offers.

Reliability Requirements

Offers must meet minimum reliability:

reliability_min: 0.98

Provider offers below this threshold are excluded.

Interruptible Instances

Configuration:

allow_interruptible: true

Determines whether preemptible instances are allowed.

Interruptible instances are cheaper but may terminate unexpectedly.

Pricing Constraints

Maximum hourly price:

max_dph: 0.6

Offers exceeding this price are excluded.

Final Resource Model

The sizing engine outputs:

required_vram_gb
required_disk_gb
required_network_down_mbps
required_network_up_mbps

These values are passed to the offer selection engine.