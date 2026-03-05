Purpose

DeepSeek provides the LLM inference runtime used by ai-orchestrator.

The implementation uses:

llama.cpp

via:

llama-cpp-python
Runtime Endpoint

DeepSeek exposes an HTTP endpoint:

http://<instance-ip>:8080
Service Responsibilities

DeepSeek handles:

text generation

token streaming

inference requests

Model Execution

Models run locally on the GPU.

Expected GPU usage:

~24 GB VRAM

depending on the model variant.

Bootstrap Commands

Typical runtime startup:

python -m llama_cpp.server \
  --port 8080 \
  --model /models/deepseek.gguf
Health Check Endpoint

DeepSeek readiness checks verify:

GET /

returns a successful HTTP response.

Resource Requirements

Typical requirements:

Resource	Requirement
GPU VRAM	≥ 24 GB
Disk	model dependent
Network	moderate
Plugin Integration

The DeepSeek plugin provides:

plugins/deepseek_llamacpp.py

Responsibilities:

sizing requirements

bootstrap commands

runtime configuration