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
