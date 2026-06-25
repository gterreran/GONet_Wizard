# GONet_Wizard/ui/runtime.py

"""
UI Runtime Mode and Event Loop Control
======================================

This module centralizes process-level runtime controls for the GONet Wizard UI.
It provides:

- a simple environment-variable mechanism to indicate that the current process
  is already running inside a GUI/webview context, and
- a process-local guard to ensure :func:`webview.start` is invoked at most once.

These utilities allow CLI command handlers to be reused from GUI workflows
without accidentally starting additional pywebview loops. The module also
re-exports a stable helper for ensuring the unified UI server is running.

Constants
---------
:data:`CONFIG`
    :class:`.UIRuntimeConfig` instance defining runtime configuration defaults.

Classes
-------
:class:`UIRuntimeConfig`
    Configuration values used to determine UI mode behavior.
:class:`._WebviewLoopState`
    Internal state tracking whether the pywebview loop has been started.

Functions
---------
:func:`set_launcher_mode`
    Mark the current process as running inside the GUI launcher.
:func:`in_launcher_mode`
    Check whether the process is running inside a GUI/webview loop.
:func:`start_webview_loop`
    Start the pywebview event loop exactly once per process.
:func:`start_event_loop_if_needed`
    Backwards-compatible wrapper around :func:`start_webview_loop`.
:func:`ensure_server_running`
    Ensure the unified UI server is running and return the selected port.

"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Environment variable used to signal we're already inside a running UI process
# (i.e., pywebview.start() is already running).
_UI_MODE_ENV = "GONET_WIZARD_UI_MODE"


@dataclass(frozen=True)
class UIRuntimeConfig:
    """
    Configuration for determining UI runtime behavior.

    Attributes
    ----------
    ui_mode_env : :class:`str`
        Environment variable name used to signal UI mode.
    """
    ui_mode_env: str = _UI_MODE_ENV


CONFIG = UIRuntimeConfig()


def set_launcher_mode() -> None:
    """
    Mark the current process as a running UI process.

    This is intended for environments where GUI code invokes CLI handlers
    internally. In that situation, downstream handler wrappers should avoid
    starting a new pywebview loop because it is already running.

    Returns
    -------
    None
    """
    os.environ[CONFIG.ui_mode_env] = "launcher"


def in_launcher_mode() -> bool:
    """
    Determine whether the current process is running in launcher mode.

    Returns
    -------
    :class:`bool`
        ``True`` if the process has been marked as running inside a GUI/webview
        loop; otherwise ``False``.
    """
    return os.environ.get(CONFIG.ui_mode_env, "").lower() == "launcher"


@dataclass
class _WebviewLoopState:
    """
    Process-local state tracking whether the pywebview loop has been started.

    Attributes
    ----------
    started : :class:`bool`
        ``True`` once :func:`webview.start` has been invoked in this process.

    Notes
    -----
    :func:`webview.start` must be called at most once per process.
    """
    started: bool = False


_STATE = _WebviewLoopState()


def start_webview_loop(
    *,
    debug_webview: bool = False,
    private_mode: bool = False,
    force: bool = False,
) -> None:
    """
    Start the pywebview event loop exactly once per process.

    Calls to this function are idempotent. If the loop has already been started,
    the function returns immediately.

    Parameters
    ----------
    debug_webview : :class:`bool`, optional
        Enable pywebview debug mode. Defaults to ``False``.
    private_mode : :class:`bool`, optional
        Enable pywebview private mode. Defaults to ``False``.
    force : :class:`bool`, optional
        If ``True``, start the loop even if :func:`in_launcher_mode` is ``True``.
        Defaults to ``False``.

    Returns
    -------
    None
    """
    if in_launcher_mode() and not force:
        return

    if _STATE.started:
        return

    import webview

    _STATE.started = True
    webview.start(debug=debug_webview, private_mode=private_mode)


def start_event_loop_if_needed(*, debug: bool = False) -> None:
    """
    Backwards-compatible wrapper for legacy call sites.

    Parameters
    ----------
    debug : :class:`bool`, optional
        If ``True``, enable pywebview debug mode.

    Returns
    -------
    None
    """
    start_webview_loop(debug_webview=debug)


def ensure_server_running(port: int = 5050) -> int:
    """
    Ensure the unified UI server is running and return the port.

    This is implemented in :mod:`GONet_Wizard.ui.server` and imported here to
    provide a stable public API for command wrappers and UI entry points.

    Parameters
    ----------
    port : :class:`int`, optional
        Preferred port for the unified UI server. Defaults to ``5050``.

    Returns
    -------
    :class:`int`
        The port on which the server is running.

    Raises
    ------
    RuntimeError
        If the server cannot be started.
    """
    from GONet_Wizard.ui.server import ensure_server_running as _ensure

    return _ensure(port=port)
