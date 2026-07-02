"""
Show Metadata Save Session Registry
==================================

This module stores short-lived session state for interactive ``show_meta``
windows. A session is registered when ``show_meta --html`` opens a preview window
and is consumed when the user clicks ``Save PDF`` or ``Exit`` in that window.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class ShowMetaSession:
    """Short-lived state associated with an interactive ``show_meta`` window.

    Parameters
    ----------
    session_id : :class:`str`
        Unique identifier embedded in the interactive HTML page.
    files : :class:`list` of :class:`str`
        Input file paths used to build the metadata view.
    terminal_stream : :class:`object` or None
        Deferred GUI terminal stream bridge used by ``/run/stream``. This is
        ``None`` for normal CLI launches.
    """

    session_id: str
    files: list[str]
    terminal_stream: Any | None = None


class ShowMetaSessionRegistry:
    """Thread-safe registry of active ``show_meta`` sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, ShowMetaSession] = {}
        self._lock = Lock()

    def register(self, session: ShowMetaSession) -> None:
        """Register or replace a session by identifier."""
        with self._lock:
            self._sessions[session.session_id] = session

    def pop(self, session_id: str) -> ShowMetaSession | None:
        """Remove and return a session if it exists."""
        with self._lock:
            return self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> ShowMetaSession | None:
        """Return a session without removing it."""
        with self._lock:
            return self._sessions.get(session_id)


show_meta_session_registry = ShowMetaSessionRegistry()

__all__ = ["ShowMetaSession", "ShowMetaSessionRegistry", "show_meta_session_registry"]
