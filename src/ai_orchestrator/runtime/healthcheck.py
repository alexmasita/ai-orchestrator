from __future__ import annotations

import socket
import time

try:
    import requests as _requests
except Exception:  # pragma: no cover
    _requests = None


class _RequestsFallback:
    @staticmethod
    def get(*_args, **_kwargs):
        raise RuntimeError("requests not available")


requests = _requests if _requests is not None else _RequestsFallback()


def wait_for_port(host: str, port: int, timeout: float) -> bool:
    deadline = time.monotonic() + float(timeout)
    while True:
        try:
            connection = socket.create_connection((host, int(port)), timeout=1.0)
            if hasattr(connection, "close"):
                connection.close()
            return True
        except OSError:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for port {host}:{port}")
            time.sleep(0.1)


def wait_for_http(url: str, timeout: float) -> bool:
    deadline = time.monotonic() + float(timeout)
    while True:
        try:
            response = requests.get(url, timeout=1.0)
            if response.status_code == 200:
                return True
        except Exception:
            pass

        if time.monotonic() >= deadline:
            raise RuntimeError(f"Timed out waiting for HTTP endpoint {url}")
        time.sleep(0.1)


def wait_for_instance_ready(
    host: str,
    deepseek_port: int = 8080,
    whisper_port: int = 9000,
    deepseek_url: str | None = None,
    whisper_url: str | None = None,
    timeout: float = 30.0,
) -> bool:
    resolved_deepseek_url = deepseek_url or f"http://{host}:{int(deepseek_port)}"
    resolved_whisper_url = whisper_url or f"http://{host}:{int(whisper_port)}"

    wait_for_port(host, deepseek_port, timeout)
    wait_for_port(host, whisper_port, timeout)
    wait_for_http(resolved_deepseek_url, timeout)
    wait_for_http(resolved_whisper_url, timeout)
    return True

