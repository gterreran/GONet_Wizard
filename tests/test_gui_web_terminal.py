from __future__ import annotations

from flask import Flask

from GONet_Wizard.commands.smart_parser import SmartArgumentParser
from GONet_Wizard.gui import web
from GONet_Wizard.logging_utils import get_logger


def _fake_app(parser, monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(web.launcher_bp)
    monkeypatch.setattr(web, "_CLI_PARSER", parser)
    return app


def _parser_with_handler(handler):
    parser = SmartArgumentParser(description="test")
    subparsers = parser.add_subparsers(dest="command", parser_class=parser.__class__)
    command = subparsers.add_parser("fake")
    command.set_defaults(handler=handler)
    return parser


def test_run_command_returns_captured_terminal_feedback(monkeypatch):
    logger = get_logger("test_gui_web_terminal")

    def handler(args):
        print("stdout progress")
        logger.info("logged progress")
        return "<p>done</p>"

    app = _fake_app(_parser_with_handler(handler), monkeypatch)

    with app.test_client() as client:
        response = client.post("/run", json={"command": "fake"})

    data = response.get_json()

    assert data["status"] == "success"
    assert data["output"] == "<p>done</p>"
    assert "$ GONet_Wizard fake" in data["terminal"]
    assert "SUCCESS:" in data["terminal"]
    assert "stdout progress" in data["terminal"]
    assert "logged progress" in data["terminal"]


def test_run_command_returns_traceback_in_terminal_feedback(monkeypatch):
    def handler(args):
        print("before failure")
        raise RuntimeError("boom")

    app = _fake_app(_parser_with_handler(handler), monkeypatch)

    with app.test_client() as client:
        response = client.post("/run", json={"command": "fake"})

    data = response.get_json()

    assert data["status"] == "error"
    assert data["message"] == "boom"
    assert "ERROR: boom" in data["terminal"]
    assert "before failure" in data["terminal"]
    assert "[traceback]" in data["terminal"]
    assert "RuntimeError: boom" in data["terminal"]


def test_stream_command_emits_live_terminal_feedback(monkeypatch):
    logger = get_logger("test_gui_web_terminal")

    def handler(args):
        print("stdout progress")
        logger.info("logged progress")
        return "<p>done</p>"

    app = _fake_app(_parser_with_handler(handler), monkeypatch)

    with app.test_client() as client:
        response = client.post("/run/stream", json={"command": "fake"})

    text = response.get_data(as_text=True)

    assert response.mimetype == "text/event-stream"
    assert "event: terminal" in text
    assert "$ GONet_Wizard fake" in text
    assert "stdout progress" in text
    assert "logged progress" in text
    assert "SUCCESS: Command finished." in text
    assert "Output: <p>done</p>" in text
    assert "SUCCESS: Executed:" not in text
    assert "event: done" in text
    assert '"status": "success"' in text
    assert '"message": "Command finished."' in text
    assert '"output": "<p>done</p>"' in text


def test_stream_command_emits_traceback_feedback(monkeypatch):
    def handler(args):
        print("before failure")
        raise RuntimeError("boom")

    app = _fake_app(_parser_with_handler(handler), monkeypatch)

    with app.test_client() as client:
        response = client.post("/run/stream", json={"command": "fake"})

    text = response.get_data(as_text=True)

    assert response.mimetype == "text/event-stream"
    assert "before failure" in text
    assert "ERROR: boom" in text
    assert "[traceback]" in text
    assert "RuntimeError: boom" in text
    assert "event: done" in text
    assert '"status": "error"' in text


def test_close_show_session_finishes_terminal_stream(monkeypatch):
    from GONet_Wizard.commands.show.session import ShowSaveSession, show_session_registry

    class DummyTerminalStream:
        def __init__(self):
            self.calls = []

        def append(self, text, *, status="running"):
            self.calls.append(("append", text, status))

        def finish(self, **kwargs):
            self.calls.append(("finish", kwargs))

    terminal_stream = DummyTerminalStream()
    show_session_registry.register(
        ShowSaveSession(
            session_id="show-session-test",
            files=["x.jpg"],
            channels=["blue"],
            window_width_px=1200,
            window_height_px=700,
            terminal_stream=terminal_stream,
        )
    )

    app = _fake_app(_parser_with_handler(lambda args: None), monkeypatch)
    with app.test_client() as client:
        response = client.post(
            "/show/session/show-session-test/close",
            json={"save_path": ""},
        )

    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert terminal_stream.calls[-1][0] == "finish"
    assert terminal_stream.calls[-1][1]["message"] == "Show window closed without saving."


def test_close_show_session_saves_figure(monkeypatch):
    from GONet_Wizard.commands.show.session import ShowSaveSession, show_session_registry

    saved = {}

    def fake_build_show_figure(files, **kwargs):
        saved["files"] = files
        saved["channels"] = kwargs["channels"]
        return object()

    def fake_save(fig, save_path):
        saved["path"] = save_path
        saved["figure"] = fig
        return "/tmp/final.pdf"

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}
        def start(self):
            if self._target is None:
                return
            if getattr(self._target, "__name__", "") == "_dot_worker":
                return
            self._target(*self._args, **self._kwargs)
        def join(self, timeout=None):
            return None

    monkeypatch.setattr("GONet_Wizard.commands.show.figure.build_show_figure", fake_build_show_figure)
    monkeypatch.setattr("GONet_Wizard.commands.show.io.save_figure_plotly", fake_save)
    monkeypatch.setattr(web, "_request_show_window_close", lambda: None, raising=False)
    monkeypatch.setattr(web.threading, "Thread", ImmediateThread)

    show_session_registry.register(
        ShowSaveSession(
            session_id="show-save-test",
            files=["requested.jpg"],
            channels=["red", "green"],
            window_width_px=1111,
            window_height_px=777,
        )
    )

    app = _fake_app(_parser_with_handler(lambda args: None), monkeypatch)
    with app.test_client() as client:
        response = client.post(
            "/show/session/show-save-test/close",
            json={"save_path": "requested.pdf"},
        )

    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["save_path"] == "requested.pdf"
    assert saved["path"] == "requested.pdf"
    assert saved["files"] == ["requested.jpg"]
    assert saved["channels"] == ["red", "green"]
