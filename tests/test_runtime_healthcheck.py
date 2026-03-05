import importlib

import pytest


HEALTHCHECK_MODULE = "ai_orchestrator.runtime.healthcheck"


def _load_healthcheck_module():
    return importlib.import_module(HEALTHCHECK_MODULE)


def test_healthcheck_module_import_path():
    module = _load_healthcheck_module()
    assert module.__name__ == HEALTHCHECK_MODULE


def test_healthcheck_functions_exist():
    module = _load_healthcheck_module()
    assert hasattr(module, "wait_for_port")
    assert callable(module.wait_for_port)
    assert hasattr(module, "wait_for_http")
    assert callable(module.wait_for_http)
    assert hasattr(module, "wait_for_instance_ready")
    assert callable(module.wait_for_instance_ready)


def test_wait_for_port_retries_then_succeeds(monkeypatch):
    module = _load_healthcheck_module()
    attempts = {"count": 0}
    sleeps = []

    def _fake_create_connection(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError("not ready")
        return object()

    def _fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(module.socket, "create_connection", _fake_create_connection, raising=False)
    monkeypatch.setattr(module.time, "sleep", _fake_sleep, raising=False)

    assert module.wait_for_port("127.0.0.1", 8080, timeout=5) is True
    assert attempts["count"] >= 3
    assert len(sleeps) >= 1


def test_wait_for_port_timeout_raises_runtime_error(monkeypatch):
    module = _load_healthcheck_module()
    sleeps = []
    monotonic_values = iter([0.0, 0.3, 0.6, 1.1, 1.4])

    def _fake_create_connection(*_args, **_kwargs):
        raise OSError("still down")

    def _fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(
        module.socket, "create_connection", _fake_create_connection, raising=False
    )
    monkeypatch.setattr(module.time, "sleep", _fake_sleep, raising=False)
    monkeypatch.setattr(module.time, "monotonic", lambda: next(monotonic_values), raising=False)

    with pytest.raises(RuntimeError):
        module.wait_for_port("127.0.0.1", 8080, timeout=1.0)
    assert len(sleeps) >= 1


def test_wait_for_http_success_returns_true(monkeypatch):
    module = _load_healthcheck_module()
    sleeps = []

    class _Resp:
        def __init__(self, status_code):
            self.status_code = status_code

    monkeypatch.setattr(
        module.requests,
        "get",
        lambda *_args, **_kwargs: _Resp(200),
        raising=False,
    )
    monkeypatch.setattr(module.time, "sleep", lambda s: sleeps.append(s), raising=False)

    assert module.wait_for_http("http://127.0.0.1:8080/health", timeout=2.0) is True
    assert sleeps == []


def test_wait_for_http_timeout_raises_runtime_error(monkeypatch):
    module = _load_healthcheck_module()
    sleeps = []
    monotonic_values = iter([0.0, 0.4, 0.8, 1.2, 1.6])

    def _raise_http_error(*_args, **_kwargs):
        raise RuntimeError("http down")

    monkeypatch.setattr(module.requests, "get", _raise_http_error, raising=False)
    monkeypatch.setattr(module.time, "sleep", lambda s: sleeps.append(s), raising=False)
    monkeypatch.setattr(module.time, "monotonic", lambda: next(monotonic_values), raising=False)

    with pytest.raises(RuntimeError):
        module.wait_for_http("http://127.0.0.1:8080/health", timeout=1.0)
    assert len(sleeps) >= 1


def test_wait_for_instance_ready_calls_port_and_http(monkeypatch):
    module = _load_healthcheck_module()
    calls = {"port": [], "http": []}

    def _fake_wait_for_port(host, port, timeout):
        calls["port"].append((host, port, timeout))
        return True

    def _fake_wait_for_http(url, timeout):
        calls["http"].append((url, timeout))
        return True

    monkeypatch.setattr(module, "wait_for_port", _fake_wait_for_port, raising=False)
    monkeypatch.setattr(module, "wait_for_http", _fake_wait_for_http, raising=False)
    monkeypatch.setattr(module.time, "sleep", lambda _s: None, raising=False)

    assert module.wait_for_instance_ready("127.0.0.1", timeout=5.0) is True
    assert len(calls["port"]) >= 1
    assert len(calls["http"]) >= 1


def test_wait_for_instance_ready_raises_runtime_error_on_failure(monkeypatch):
    module = _load_healthcheck_module()

    monkeypatch.setattr(module, "wait_for_port", lambda *_a, **_k: True, raising=False)
    monkeypatch.setattr(
        module,
        "wait_for_http",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("health failed")),
        raising=False,
    )
    monkeypatch.setattr(module.time, "sleep", lambda _s: None, raising=False)

    with pytest.raises(RuntimeError):
        module.wait_for_instance_ready("127.0.0.1", timeout=5.0)
