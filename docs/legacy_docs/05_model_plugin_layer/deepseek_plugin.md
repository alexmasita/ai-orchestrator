Overview

The DeepSeek plugin defines requirements and runtime configuration for the DeepSeek LLM service using llama.cpp.

Plugin file:

src/ai_orchestrator/plugins/deepseek_llamacpp.py
Model Role

DeepSeek provides:

language model inference

HTTP API service

Service Port

DeepSeek runs on:

8080

The readiness probe checks:

http://<instance_ip>:8080
Resource Requirements

Typical resource requirements:

Resource	Requirement
GPU VRAM	~20–24 GB
Disk	~10 GB
Network	moderate

Exact VRAM requirement is determined by model configuration.

Runtime Behavior

During bootstrap:

model binaries downloaded

llama.cpp server started

HTTP service exposed

Startup command example:

./server --port 8080 --model deepseek.gguf
Bootstrap Responsibilities

The plugin contributes commands to the bootstrap script.

Example tasks:

install dependencies

download model

start inference server

Healthcheck

Readiness check:

http://<instance_ip>:8080

The healthcheck system waits for this endpoint before marking the instance ready.