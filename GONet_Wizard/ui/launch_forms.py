# GONet_Wizard/ui/launch_forms.py

"""
Command Form Launcher Utilities
===============================

This module provides a small helper to open a specific command form page served
by the unified local UI server in a managed pywebview window.

The primary use case is routing CLI invocations to the GUI form for a command
when the invocation includes only the command token sequence and omits required
arguments. The helper ensures the unified UI server is running, loads the
appropriate ``/cmd/...`` route, and starts the pywebview event loop if needed.

Functions
---------

:func:`.open_command_form`
    Ensure the unified UI server is running and load the command form page in a
    managed launcher window.

"""

from __future__ import annotations

from typing import Sequence

from GONet_Wizard.ui.runtime import ensure_server_running, start_webview_loop
from GONet_Wizard.ui.windows import WindowSpec
from GONet_Wizard.ui import WINDOWS


def open_command_form(
    *,
    cmd_tokens: Sequence[str],
    port: int,
    debug_webview: bool,
) -> None:
    """
    Open a GUI command form page in the managed launcher window.

    The command form URL is derived from ``cmd_tokens`` and points to the unified
    UI server route ``/cmd/<path>``. The window is created or reused under the
    stable key ``"launcher"``.

    Parameters
    ----------
    cmd_tokens : :class:`~typing.Sequence` of :class:`str`
        Command token sequence identifying the command form to load (e.g.,
        ``("show",)`` or ``("connect", "snap")``). Tokens are joined with ``"/"``
        to form the form route path.
    port : :class:`int`
        Preferred port for the unified local UI server.
    debug_webview : :class:`bool`
        If ``True``, start the pywebview event loop with debugging enabled.

    Returns
    -------
    None
        This function does not return a value.

    Raises
    ------
    :class:`RuntimeError`
        If the unified UI server cannot be started or the window cannot be
        created.
    """
    port = ensure_server_running(port=port)

    cmd_path = "/".join(cmd_tokens)
    title = f"GONet — {' '.join(cmd_tokens)}"

    WINDOWS.ensure(
        "launcher",
        WindowSpec(
            title=title,
            url=f"http://127.0.0.1:{port}/cmd/{cmd_path}",
            width=1100,
            height=750,
        ),
    )

    start_webview_loop(debug_webview=debug_webview)

