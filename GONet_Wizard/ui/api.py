# GONet_Wizard/ui/api.py

"""
PyWebview JavaScript API Bridge
===============================

This module defines the Python-side JavaScript API exposed to pywebview windows
as ``window.pywebview.api``. The API provides a small set of UI affordances that
frontend pages can invoke to interact with the host OS, such as:

- opening native file/folder selection dialogs, and
- triggering window management actions (e.g., closing a window).

The API is intentionally lightweight and uses lazy imports to avoid importing
:mod:`webview` at import time. File dialog actions are debounced and guarded by
a lock to prevent double-triggered dialogs from rapid user interactions.

Classes
-------
:class:`WebviewAPI`
    JavaScript API object exposed by pywebview as ``window.pywebview.api``.

"""

from __future__ import annotations

import json
import threading
import time
from typing import List, Any, Sequence
from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)


class WebviewAPI:
    """
    JavaScript API for pywebview interactions.

    Instances of this class are attached to pywebview windows and are accessible
    from JavaScript as ``window.pywebview.api``.

    Attributes
    ----------
    _dialog_lock : :class:`threading.Lock`
        Lock guarding access to native dialog creation.
    _last_dialog_t : :class:`float`
        Timestamp of the last dialog invocation used for debouncing.
    """

    def __init__(self) -> None:
        """
        Initialize the JavaScript API bridge.

        Returns
        -------
        None
        """
        self._dialog_lock = threading.Lock()
        self._last_dialog_t = 0.0

    def _webview(self):
        """
        Lazily import and return the :mod:`webview` module.

        Returns
        -------
        :class:`module`
            Imported :mod:`webview` module.
        """
        import webview
        return webview

    def _save_dialog_kind(self):
        """
        Return the pywebview save-dialog enum with backward compatibility.

        Returns
        -------
        object
            ``webview.FileDialog.SAVE`` on modern pywebview versions, falling
            back to the deprecated ``webview.SAVE_DIALOG`` constant when needed.
        """
        webview = self._webview()
        file_dialog = getattr(webview, "FileDialog", None)
        save_kind = getattr(file_dialog, "SAVE", None) if file_dialog is not None else None
        return save_kind if save_kind is not None else webview.SAVE_DIALOG

    def _window0(self):
        """
        Return the first pywebview window.

        Returns
        -------
        :class:`webview.Window`
            The first available pywebview window.

        Raises
        ------
        RuntimeError
            If no pywebview windows are available.
        """
        webview = self._webview()
        if not getattr(webview, "windows", None):
            raise RuntimeError("No pywebview windows are available.")
        return webview.windows[0]

    def _as_list(self, result: Any) -> List[str]:
        """
        Normalize a dialog return value into a list of string paths.

        Parameters
        ----------
        result : :class:`object`
            Value returned by a pywebview dialog call.

        Returns
        -------
        :class:`list` of :class:`str`
            List of string paths (possibly empty).
        """
        if not result:
            return []
        if isinstance(result, (list, tuple)):
            return [str(p) for p in result]
        return [str(result)]

    def close_window(self) -> None:
        """
        Close the first pywebview window.

        Returns
        -------
        None

        Notes
        -----
        Window destruction is scheduled on a short timer to avoid interfering
        with the calling JavaScript event loop.
        """
        threading.Timer(0.1, lambda: self._window0().destroy()).start()

    def pick_paths(self, mode: str = "files") -> List[str]:
        """
        Open a native file/folder dialog and return selected paths.

        Parameters
        ----------
        mode : :class:`str`, optional
            Selection mode:

            - ``"files"``: file picker (multi-select)
            - ``"folder"``: folder picker (single)

        Returns
        -------
        :class:`list` of :class:`str`
            Selected paths, or an empty list on cancel.

        Notes
        -----
        Dialog creation is debounced and guarded by a lock to prevent duplicate
        dialogs from rapid user interactions.
        """
        now = time.time()

        if now - self._last_dialog_t < 0.35:
            return []

        if not self._dialog_lock.acquire(blocking=False):
            return []

        self._last_dialog_t = now
        try:
            webview = self._webview()
            win = self._window0()

            mode_norm = (mode or "files").strip().lower()
            if mode_norm in {"dir", "directory"}:
                mode_norm = "folder"

            if mode_norm == "folder":
                result = win.create_file_dialog(
                    webview.FileDialog.FOLDER,
                    allow_multiple=False,
                )
                return self._as_list(result)

            # default: files
            result = win.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=True,
            )
            return self._as_list(result)

        finally:
            self._dialog_lock.release()


    def close_named_window(self, key: str) -> None:
        """
        Close a registered pywebview window by key.

        Parameters
        ----------
        key : :class:`str`
            Window registry key.

        Returns
        -------
        None
        """
        from GONet_Wizard.ui.windows import WINDOWS
        threading.Timer(0.05, lambda: WINDOWS.close(str(key))).start()

    def _normalize_file_types(self, file_types: Any | None) -> tuple[str, ...]:
        """
        Normalize JavaScript-provided file type filters for a save dialog.

        Parameters
        ----------
        file_types : object or None
            A string or sequence of strings accepted by pywebview's
            ``create_file_dialog(..., file_types=...)`` argument.

        Returns
        -------
        tuple of str
            File type filters suitable for :mod:`pywebview`.
        """
        if not file_types:
            return (
                "PDF files (*.pdf)",
                "PNG files (*.png)",
                "JPEG files (*.jpg;*.jpeg)",
                "SVG files (*.svg)",
                "HTML files (*.html;*.htm)",
                "All files (*.*)",
            )
        if isinstance(file_types, str):
            return (file_types,)
        if isinstance(file_types, Sequence):
            normalized = tuple(str(item) for item in file_types if str(item))
            return normalized or ("All files (*.*)",)
        return ("All files (*.*)",)

    def pick_save_path(
        self,
        default_name: str = "gonet_figure.pdf",
        file_types: Any | None = None,
    ) -> str:
        """
        Open a native save dialog and return the selected output path.

        Parameters
        ----------
        default_name : :class:`str`, optional
            Suggested filename shown by the OS save dialog.
        file_types : object, optional
            Optional pywebview file type filters. JavaScript callers may pass a
            list such as ``["PDF files (*.pdf)", "All files (*.*)"]``.

        Returns
        -------
        :class:`str`
            Selected save path, or an empty string when the dialog is canceled.
        """
        now = time.time()

        if now - self._last_dialog_t < 0.35:
            return ""

        if not self._dialog_lock.acquire(blocking=False):
            return ""

        self._last_dialog_t = now
        try:
            webview = self._webview()
            win = self._window0()
            if not hasattr(win, "create_file_dialog"):
                logger.warning("Save dialog not supported in current backend.")
                return ""

            result = win.create_file_dialog(
                self._save_dialog_kind(),
                save_filename=default_name,
                file_types=self._normalize_file_types(file_types),
            )
            paths = self._as_list(result)
            return paths[0] if paths else ""
        finally:
            self._dialog_lock.release()

    def download_json(self, data: dict) -> None:
        """
        Save a dictionary as a JSON file using a native save dialog.

        Parameters
        ----------
        data : :class:`dict`
            JSON-serializable dictionary to write.

        Returns
        -------
        None

        Raises
        ------
        OSError
            If the selected output path cannot be written.
        TypeError
            If ``data`` is not JSON serializable.
        """
        webview = self._webview()
        window = webview.windows[0]

        if not hasattr(window, "create_file_dialog"):
            logger.warning("File dialog not supported in current backend.")
            return

        path = window.create_file_dialog(
            self._save_dialog_kind(),
            file_types=("JSON files (*.json)", "All files (*.*)"),
        )

        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
