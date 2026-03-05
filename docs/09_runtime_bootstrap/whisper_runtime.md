Purpose

Whisper provides speech-to-text inference capability.

It runs alongside the LLM runtime.

Runtime Endpoint

Whisper exposes:

http://<instance-ip>:9000
Runtime Implementation

Typical implementation uses:

faster-whisper

or equivalent optimized inference runtime.

Bootstrap Startup Example

Example startup:

python whisper_server.py --port 9000 &
Service Responsibilities

Whisper provides:

speech recognition

audio transcription

streaming inference

Resource Requirements

Typical requirements:

Resource	Requirement
GPU VRAM	8 GB
Disk	~10 GB
Network	moderate

These values are configurable via:

config.yaml
Plugin Integration

Whisper sizing parameters are read from config:

whisper_vram_gb
whisper_disk_gb

These values are validated during:

compute_requirements()
Health Check

The orchestrator waits until the Whisper endpoint responds before returning.