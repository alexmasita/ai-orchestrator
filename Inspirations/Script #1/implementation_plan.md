My Implementation Plan:

I'll take your existing script and make these specific swaps:

Remove llama.cpp entirely — replace with vLLM (pip install vllm or use the vllm/vllm-openai image). Both LLMs will be served via vllm serve.

Two LLM services instead of one:

Architect (twhitworth/gpt-oss-120b-awq-w4a16) on port 8080 with --gpu-memory-utilization 0.45
Developer (cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit) on port 8081 with --gpu-memory-utilization 0.45
Both use vllm serve <model> --port <port> --gpu-memory-utilization 0.45
Model downloads — replace the huggingface-cli download unsloth/DeepSeek-R1-GGUF with two huggingface-cli download calls for the new models, each downloading to /workspace/models/ only if the directory doesn't already exist.

STT — Replace the custom whisper_api.py with faster-whisper-server running on CPU on port 9000 (as you specified).

TTS — Add kokoro-tts via Docker on port 9001, running on GPU (lightweight).

Control API (port 7999) — Update the /health endpoint to check all 4 ports: 8080 (Architect), 8081 (Developer), 9000 (STT), 9001 (TTS).

wait_for_port — Add health checks for all 4 ports (8080, 8081, 9000, 9001).

Idle monitor — Update to check both LLM ports + STT + TTS for activity.

State file — Update the ports JSON to reflect all 4 services.

Vast.ai integration stays identical — self_destroy uses DELETE /api/v0/instances/{id}/, /stop uses PUT /api/v0/instances/{id}/ {"state": "stopped"}, VAST_CONTAINERLABEL for instance ID, onstart field for launching. All documented at /api-reference/creating-instances-with-api and confirmed in the OpenAPI spec.

Key architectural note: Since you're targeting A100/H100 80GB and splitting VRAM 0.45/0.45, that leaves ~10% headroom for kokoro-tts (which you said is ultra-lightweight on GPU). The two vLLM processes will share the single GPU.

Shall I proceed with generating the script?