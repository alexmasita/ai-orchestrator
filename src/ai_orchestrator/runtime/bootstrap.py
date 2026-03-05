from __future__ import annotations


def deepseek_start_command() -> list[str]:
    return [
        "python3",
        "-m",
        "deepseek_server",
        "--host",
        "0.0.0.0",
        "--port",
        "8080",
    ]


def whisper_start_command() -> list[str]:
    return [
        "uvicorn",
        "whisper_api:app",
        "--host",
        "0.0.0.0",
        "--port",
        "9000",
    ]

