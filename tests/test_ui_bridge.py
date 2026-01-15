from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest


def _install_fake_windows_module(monkeypatch):
    """
    Install a fake `GONet_Wizard.ui.windows` module containing a WindowSpec dataclass.

    This prevents tests from importing the real `windows.py`, which imports webview
    at import-time.
    """
    fake_mod = types.ModuleType("GONet_Wizard.ui.windows")

    @dataclass
    class WindowSpec:
        title: str
        url: str
        width: int = 1200
        height: int = 800
        resizable: bool = True

    fake_mod.WindowSpec = WindowSpec
    monkeypatch.setitem(sys.modules, "GONet_Wizard.ui.windows", fake_mod)
    return WindowSpec


@pytest.fixture
def runtime_spies(monkeypatch):
    """
    Patch runtime hooks used by ui_bridge to prevent starting any real services.
    """
    calls = {
        "ensure_server_running": [],
        "start_webview_loop": [],
    }

    def fake_ensure_server_running(*, port: int = 5050) -> int:
        calls["ensure_server_running"].append(port)
        return port

    def fake_start_webview_loop(*, debug_webview: bool = False, private_mode: bool = False, force: bool = False) -> None:
        calls["start_webview_loop"].append(
            {"debug_webview": debug_webview, "private_mode": private_mode, "force": force}
        )

    monkeypatch.setattr("GONet_Wizard.ui.runtime.ensure_server_running", fake_ensure_server_running, raising=True)
    monkeypatch.setattr("GONet_Wizard.ui.runtime.start_webview_loop", fake_start_webview_loop, raising=True)

    return calls


@pytest.fixture
def bridge_spies(monkeypatch):
    """
    Patch ui_bridge internal side-effect functions so we can assert calls.
    """
    from GONet_Wizard.commands import ui_bridge

    calls = {
        "publish": [],
        "ensure_window": [],
    }

    def fake_publish(req):
        calls["publish"].append(req)

    def fake_ensure_window(req):
        calls["ensure_window"].append(req)

    monkeypatch.setattr(ui_bridge, "_publish_html", fake_publish, raising=True)
    monkeypatch.setattr(ui_bridge, "_ensure_window", fake_ensure_window, raising=True)

    return calls


def test_realize_none_returns_false(runtime_spies, bridge_spies):
    from GONet_Wizard.commands.ui_bridge import realize_ui_result

    requested = realize_ui_result("show", None, port=5050)
    assert requested is False
    assert bridge_spies["publish"] == []
    assert bridge_spies["ensure_window"] == []
    assert runtime_spies["ensure_server_running"] == []


def test_realize_publish_only(runtime_spies, bridge_spies):
    from GONet_Wizard.commands.ui_bridge import realize_ui_result, PublishRequest

    req = PublishRequest(channel="x", html="<html/>", title="T")
    requested = realize_ui_result("show", req, port=5050)

    assert requested is False
    assert len(bridge_spies["publish"]) == 1
    assert bridge_spies["publish"][0].channel == "x"
    assert bridge_spies["ensure_window"] == []
    # publish-only should not force server start in current implementation
    assert runtime_spies["ensure_server_running"] == []


def test_realize_window_request_without_publish(runtime_spies, bridge_spies):
    from GONet_Wizard.commands.ui_bridge import realize_ui_result, WindowRequest

    # A minimal spec object is fine; ui_bridge just passes it through to _ensure_window
    spec = object()
    req = WindowRequest(key="k", spec=spec, publish=None)

    requested = realize_ui_result("show", req, port=5051)

    assert requested is True
    assert runtime_spies["ensure_server_running"] == [5051]
    assert bridge_spies["publish"] == []
    assert len(bridge_spies["ensure_window"]) == 1
    assert bridge_spies["ensure_window"][0].key == "k"
    assert bridge_spies["ensure_window"][0].spec is spec


def test_realize_window_request_with_publish(runtime_spies, bridge_spies):
    from GONet_Wizard.commands.ui_bridge import realize_ui_result, WindowRequest, PublishRequest

    spec = object()
    pub = PublishRequest(channel="chan", html="<html/>", title="Title")
    req = WindowRequest(key="win", spec=spec, publish=pub)

    requested = realize_ui_result("show", req, port=5052)

    assert requested is True
    assert runtime_spies["ensure_server_running"] == [5052]
    assert len(bridge_spies["publish"]) == 1
    assert bridge_spies["publish"][0].channel == "chan"
    assert len(bridge_spies["ensure_window"]) == 1
    assert bridge_spies["ensure_window"][0].key == "win"


def test_realize_legacy_html_string_normalizes_to_preview_window(monkeypatch, runtime_spies, bridge_spies):
    """
    Legacy behavior: returning a raw HTML string should publish to channel=cmd_name
    and open /view/<cmd_name>.
    """
    WindowSpec = _install_fake_windows_module(monkeypatch)

    from GONet_Wizard.commands.ui_bridge import realize_ui_result

    requested = realize_ui_result("my_command", "<html>ok</html>", port=5999)

    assert requested is True
    assert runtime_spies["ensure_server_running"] == [5999]

    assert len(bridge_spies["publish"]) == 1
    pub = bridge_spies["publish"][0]
    assert pub.channel == "my_command"
    assert "ok" in pub.html

    assert len(bridge_spies["ensure_window"]) == 1
    winreq = bridge_spies["ensure_window"][0]
    assert winreq.key == "my_command"
    assert isinstance(winreq.spec, WindowSpec)
    assert winreq.spec.url == "http://127.0.0.1:5999/view/my_command"
    assert winreq.spec.width == 1250
    assert winreq.spec.height == 800


def test_maybe_present_ui_result_starts_loop_only_if_window_requested(monkeypatch, runtime_spies, bridge_spies):
    WindowSpec = _install_fake_windows_module(monkeypatch)

    from GONet_Wizard.commands.ui_bridge import maybe_present_ui_result, PublishRequest

    # publish-only => no loop start
    maybe_present_ui_result("cmd", PublishRequest(channel="c", html="<h/>"), port=5050, debug_webview=True)
    assert runtime_spies["start_webview_loop"] == []

    # legacy HTML string => opens window => should start loop
    maybe_present_ui_result("cmd2", "<html/>", port=5050, debug_webview=True)
    assert len(runtime_spies["start_webview_loop"]) == 1
    assert runtime_spies["start_webview_loop"][0]["debug_webview"] is True
