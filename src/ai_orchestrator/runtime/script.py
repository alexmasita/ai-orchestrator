from __future__ import annotations


def generate_bootstrap_script(config: dict, models: list[str]) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -e",
        "",
        "apt update",
        "apt install -y git build-essential cmake python3-pip curl ffmpeg",
        "",
        "git clone https://github.com/ggerganov/llama.cpp",
        "git clone https://github.com/ggerganov/whisper.cpp",
        "",
        "# model download",
        "curl -L https://huggingface.co/example/deepseek.gguf -o /tmp/deepseek.gguf",
        "",
        "# start deepseek server",
        "python3 -m deepseek_server --host 0.0.0.0 --port 8080",
        "",
        "# start whisper api",
        "uvicorn whisper_api:app --host 0.0.0.0 --port 9000",
    ]
    return "\n".join(lines).strip()

