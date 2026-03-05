Overview

The Whisper plugin defines runtime requirements for speech-to-text inference using OpenAI Whisper models.

Model Role

Whisper provides:

speech recognition

audio transcription

Service Port

Whisper runs on:

9000

Readiness endpoint:

http://<instance_ip>:9000
Required Configuration

When Whisper is enabled, configuration must include:

whisper_vram_gb
whisper_disk_gb

Example:

whisper_vram_gb: 8
whisper_disk_gb: 10
Resource Requirements
Resource	Requirement
GPU VRAM	configurable
Disk	configurable
CPU	moderate
Network	minimal

These values feed into the sizing engine.

Runtime Behavior

Bootstrap script performs:

environment setup

model download

inference server start

Example:

python whisper_server.py --port 9000
Healthcheck

Whisper readiness check:

http://<instance_ip>:9000

The orchestrator waits for both:

deepseek_url
whisper_url

before declaring success.