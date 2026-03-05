Purpose

Disk and network constraints ensure the infrastructure can download, store, and serve models reliably.

These constraints influence offer filtering.

Disk Constraints

Disk requirements include:

Component	Description
Model weights	LLM artifacts
Runtime libraries	llama.cpp binaries
Whisper runtime	speech model
Temporary files	inference buffers

Disk requirements accumulate across models.

Disk Aggregation
required_disk = sum(model_disk_requirements)

Example:

deepseek_disk_gb = 10
whisper_disk_gb = 6

Result:

required_disk = 16GB
Network Constraints

Two network dimensions are enforced.

Download bandwidth
min_inet_down_mbps

Used for:

model downloads

dependency installation

Upload bandwidth
min_inet_up_mbps

Used for:

inference responses

streaming audio

Provider Offer Filtering

Offers must satisfy:

offer.inet_down ≥ min_inet_down_mbps
offer.inet_up ≥ min_inet_up_mbps

Offers failing these constraints are excluded.