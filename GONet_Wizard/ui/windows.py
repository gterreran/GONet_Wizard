# GONet_Wizard/ui/windows.py

"""
PyWebview Window Specifications and Registry
============================================

This module provides the window-management layer for the GONet Wizard desktop
UI. It defines a lightweight, declarative :class:`.WindowSpec` used to describe
pywebview windows and a :class:`.WindowManager` that maintains a process-wide
registry of open windows under stable string keys.

The registry supports common UI workflows such as:
- opening a window once and reusing it on subsequent requests,
- focusing/reloading an existing window rather than spawning duplicates, and
- removing registry entries when a user closes a window.

The module avoids importing :mod:`webview` at import time to prevent side effects
and to keep non-GUI entry points lightweight. The singleton :data:`WINDOWS`
instance is used across the package to centralize window creation.

Type Aliases
------------
:class:`UrlLike`
    Union type accepted as a window URL, including string URLs and WSGI app-like
    objects supported by pywebview.

Classes
-------
:class:`WindowSpec`
    Declarative specification for a pywebview window (title, URL, size, flags).
:class:`WindowManager`
    Thread-safe registry for creating, retrieving, and managing pywebview windows.

Constants
---------
:data:`WINDOWS`
    Singleton :class:`.WindowManager` used across the UI layer.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Dict, Union, TYPE_CHECKING
import threading

from GONet_Wizard.ui.api import WebviewAPI

if TYPE_CHECKING:
    import webview  # only for type hints (no import-time side effects)

UrlLike = Union[str, Any]  # Any WSGI app is acceptable too


@dataclass
class WindowSpec:
    """
    Declarative specification for a pywebview window.

    Attributes
    ----------
    title : :class:`str`
        Window title.
    url : :class:`.UrlLike`
        URL string or WSGI app object.
    width : :class:`int`
        Window width in pixels.
    height : :class:`int`
        Window height in pixels.
    resizable : :class:`bool`
        Whether the window is resizable.
    on_closed : callable, optional
        Callback invoked after the window is closed and removed from the registry.
    """
    title: str
    url: UrlLike
    width: int = 1200
    height: int = 800
    resizable: bool = True
    on_closed: Optional[Callable[[], None]] = None


class WindowManager:
    """
    Thread-safe registry for pywebview windows.

    The window manager creates and tracks windows under stable keys (e.g.
    ``"launcher"``, ``"show"``, ``"dashboard"``). If a window already exists for a
    key, calls to :meth:`ensure` return the existing window and attempt a
    best-effort refresh of its URL. Closed windows are detected and removed from
    the registry so subsequent calls recreate them.

    This module does not start the pywebview event loop; it only manages window
    objects. Importing this module avoids importing :mod:`webview` to prevent
    import-time side effects.

    Attributes
    ----------
    _windows : :class:`dict`
        Mapping of window keys to pywebview window objects.
    _api : :class:`~GONet_Wizard.ui.api.WebviewAPI`
        JavaScript API instance attached to created windows.
    _lock : :class:`threading.Lock`
        Mutex protecting the window registry.
    """

    def __init__(self) -> None:
        """
        Initialize an empty window registry.

        Returns
        -------
        None
        """
        # Store windows as "Any" to avoid importing pywebview at import-time.
        self._windows: Dict[str, Any] = {}
        self._api = WebviewAPI()
        self._lock = threading.Lock()

    def _webview(self):
        """
        Lazily import and return the :mod:`webview` module.

        Returns
        -------
        :class:`module`
            The imported :mod:`webview` module.
        """
        import webview
        return webview

    def _is_closed(self, win: Any) -> bool:
        """
        Check whether a window appears to have been closed.

        Parameters
        ----------
        win : :class:`object`
            pywebview window object.

        Returns
        -------
        :class:`bool`
            ``True`` if the window exposes a close event that is set; otherwise
            ``False``.
        """
        try:
            return win.events.closed.is_set()  # threading.Event-like
        except Exception:
            return False

    def _watch_close(
        self,
        key: str,
        win: Any,
        on_closed: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Wait for a window to close and remove it from the registry.

        Parameters
        ----------
        key : :class:`str`
            Registry key associated with the window.
        win : :class:`object`
            pywebview window object to watch.
        on_closed : callable, optional
            Callback invoked after ``win`` is closed and unregistered.

        Returns
        -------
        None
        """
        should_notify = False
        try:
            win.events.closed.wait()  # blocks until closed
        finally:
            with self._lock:
                cur = self._windows.get(key)
                if cur is win:
                    self._windows.pop(key, None)
                    should_notify = True

            if should_notify and on_closed is not None:
                try:
                    on_closed()
                except Exception:
                    pass

    def ensure(self, key: str, spec: WindowSpec) -> Any:
        """
        Ensure a window exists for the given key.

        If a window already exists, it is returned and a best-effort URL refresh
        is attempted. If no window exists (or the previous one was closed), a new
        window is created, registered, and monitored for closure.

        Parameters
        ----------
        key : :class:`str`
            Stable key for the window (e.g. ``"launcher"``, ``"show"``,
            ``"dashboard"``).
        spec : :class:`.WindowSpec`
            Window configuration.

        Returns
        -------
        :class:`webview.Window`
            The created or existing window.

        Raises
        ------
        RuntimeError
            If pywebview window creation fails.
        """
        with self._lock:
            existing = self._windows.get(key)

            if existing is not None and self._is_closed(existing):
                self._windows.pop(key, None)
                existing = None

            if existing is not None:
                try:
                    existing.load_url(spec.url)
                except Exception:
                    pass
                return existing

            webview = self._webview()
            try:
                win = webview.create_window(
                    spec.title,
                    spec.url,
                    width=spec.width,
                    height=spec.height,
                    resizable=spec.resizable,
                    js_api=self._api,
                )
            except Exception as e:
                raise RuntimeError(f"Failed to create window {key!r}.") from e

            self._windows[key] = win

            t = threading.Thread(
                target=self._watch_close,
                args=(key, win, spec.on_closed),
                daemon=True,
            )
            t.start()

            return win

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a window by key, if it exists and is not closed.

        Parameters
        ----------
        key : :class:`str`
            Registry key.

        Returns
        -------
        :class:`object` or None
            The window object if present and open; otherwise ``None``.
        """
        with self._lock:
            win = self._windows.get(key)
            if win is not None and self._is_closed(win):
                self._windows.pop(key, None)
                return None
            return win

    def eval_js(self, key: str, js: str) -> None:
        """
        Evaluate JavaScript in a window (best effort).

        Parameters
        ----------
        key : :class:`str`
            Registry key of the target window.
        js : :class:`str`
            JavaScript source to evaluate.

        Returns
        -------
        None
        """
        win = self.get(key)
        if win is None:
            return
        try:
            win.evaluate_js(js)
        except Exception:
            pass

    def reload(self, key: str) -> None:
        """
        Reload the contents of a window (best effort).

        Parameters
        ----------
        key : :class:`str`
            Registry key of the target window.

        Returns
        -------
        None
        """
        self.eval_js(key, "location.reload()")

    def close(self, key: str) -> None:
        """
        Close and unregister a window (best effort).

        Parameters
        ----------
        key : :class:`str`
            Registry key of the target window.

        Returns
        -------
        None
        """
        win = self.get(key)
        if win is None:
            return
        try:
            win.destroy()
        except Exception:
            pass


# Singleton window registry used across the package/app
WINDOWS = WindowManager()
