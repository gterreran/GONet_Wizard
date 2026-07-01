"""
Show Window Save Session Registry
================================

This module stores short-lived session metadata for interactive ``show``
windows. A session is created when the ``show`` command opens a Plotly window
and remains active until the user clicks **Save figure** or **Exit**.

The registry lets the preview window callback route communicate back to the
original command invocation without coupling the HTML page directly to the
command handler. GUI-launched sessions use the stored terminal stream bridge to
append feedback to the form-page "fake" terminal, while CLI-launched sessions
fall back to normal terminal output. When the user saves, the backend rebuilds
the figure from the stored input files/channels after the viewer closes.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class ShowSaveSession:
    """Short-lived state associated with an interactive ``show`` window.

    Parameters
    ----------
    session_id : :class:`str`
        Unique identifier embedded in the interactive HTML page.
    files : :class:`list` of :class:`str`
        Input file paths used to build the show figure.
    channels : :class:`list` of :class:`str`
        Channels displayed in the show figure.
    window_width_px : :class:`int`
        Interactive show window width.
    window_height_px : :class:`int`
        Interactive show window height.
    terminal_stream : :class:`object` or None
        Deferred GUI terminal stream bridge used by ``/run/stream``.  This is
        ``None`` for normal CLI launches.
    """

    session_id: str
    files: list[str]
    channels: list[str]
    window_width_px: int
    window_height_px: int
    terminal_stream: Any | None = None


class ShowSessionRegistry:
    """Thread-safe registry of active interactive ``show`` sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, ShowSaveSession] = {}
        self._lock = Lock()

    def register(self, session: ShowSaveSession) -> None:
        """Register or replace a session by identifier."""
        with self._lock:
            self._sessions[session.session_id] = session

    def pop(self, session_id: str) -> ShowSaveSession | None:
        """Remove and return a session if it exists."""
        with self._lock:
            return self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> ShowSaveSession | None:
        """Return a session without removing it."""
        with self._lock:
            return self._sessions.get(session_id)


show_session_registry = ShowSessionRegistry()

__all__ = ["ShowSaveSession", "ShowSessionRegistry", "show_session_registry"]
