from __future__ import annotations

import threading

from GONet_Wizard.GONet_utils.src.extract_app.extract_gui import (
    _configure_extract_gui,
    cancel_interactive_extraction_if_unsubmitted,
    mark_interactive_extraction_submitted,
    app as extract_app,
)
from GONet_Wizard.ui.windows import WindowManager


class DummyTerminalStream:
    def __init__(self) -> None:
        self.calls = []
        self._done = False

    @property
    def is_done(self) -> bool:
        return self._done

    def finish(self, **kwargs) -> None:
        self.calls.append(kwargs)
        self._done = True


def test_cancel_unsubmitted_interactive_extraction_finishes_stream() -> None:
    terminal_stream = DummyTerminalStream()
    _configure_extract_gui(["image.jpg"], terminal_stream=terminal_stream)

    cancel_interactive_extraction_if_unsubmitted()

    assert terminal_stream.calls == [
        {
            "status": "error",
            "message": "Interactive extraction cancelled before output was written.",
        }
    ]
    assert extract_app.server.config.get("terminal_stream") is None


def test_cancel_unsubmitted_interactive_extraction_does_not_finish_after_submit() -> None:
    terminal_stream = DummyTerminalStream()
    _configure_extract_gui(["image.jpg"], terminal_stream=terminal_stream)
    mark_interactive_extraction_submitted()

    cancel_interactive_extraction_if_unsubmitted()

    assert terminal_stream.calls == []
    assert extract_app.server.config.get("terminal_stream") is terminal_stream


def test_window_close_watcher_invokes_on_closed_callback() -> None:
    manager = WindowManager()
    closed_event = threading.Event()

    class DummyEvents:
        closed = closed_event

    class DummyWindow:
        events = DummyEvents()

    win = DummyWindow()
    calls = []
    manager._windows["extract-gui"] = win
    closed_event.set()

    manager._watch_close("extract-gui", win, lambda: calls.append("closed"))

    assert manager.get("extract-gui") is None
    assert calls == ["closed"]
