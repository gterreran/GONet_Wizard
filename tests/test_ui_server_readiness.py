"""Tests for unified UI server health/readiness helpers."""

from __future__ import annotations

import pytest


def test_create_app_exposes_health_endpoint():
    server = pytest.importorskip("GONet_Wizard.ui.server")

    app = server.create_app()
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_wait_for_server_retries_until_health_endpoint_responds(monkeypatch):
    server = pytest.importorskip("GONet_Wizard.ui.server")
    calls = {"count": 0}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(url, timeout):
        calls["count"] += 1
        if calls["count"] < 3:
            raise OSError("not ready yet")
        return FakeResponse()

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(server.time, "sleep", lambda _: None)

    server.wait_for_server("127.0.0.1", 5050, timeout=1.0, poll_interval=0.01)

    assert calls["count"] == 3


def test_dash_runner_surfaces_background_startup_errors():
    dash_runner = pytest.importorskip("GONet_Wizard.ui.dash_runner")

    errors = dash_runner.Queue()
    errors.put(RuntimeError("synthetic startup failure"))

    with pytest.raises(RuntimeError, match="synthetic startup failure"):
        dash_runner.wait_for_port(
            "127.0.0.1",
            9,
            timeout=1.0,
            startup_errors=errors,
            app_key="test-dash-app",
        )
