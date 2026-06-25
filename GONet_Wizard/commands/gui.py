# GONet_Wizard/commands/gui.py

"""
GONet GUI Launcher Command
==========================

This module defines the ``gui`` CLI command, which launches the GONet Wizard
graphical user interface. When invoked, the command ensures that the unified
local UI server is running and opens the main launcher window using the
window-management infrastructure.

The command is declared via the :data:`COMMAND` specification and dispatched
through :func:`cli_handler`, which returns a :class:`~GONet_Wizard.commands.ui_bridge.WindowRequest`
to open the launcher window.

Constants
---------
:class:`COMMAND`
    :class:`~GONet_Wizard.commands.specs.CommandSpec` defining the ``gui`` command.

Functions
---------
:func:`cli_handler`
    CLI entry point that starts the UI server and opens the launcher window.

"""

from __future__ import annotations

import argparse

from GONet_Wizard.commands.cli_core import CommandSpec, WindowRequest
from GONet_Wizard.ui.windows import WindowSpec


COMMAND = CommandSpec(
    name="gui",
    help="Launch the GONet GUI.",
    args=[
        {
            "flags": ["--port"],
            "type": int,
            "default": 5050,
            "help": "Port for the unified local UI server.",
        }
    ],
)


def cli_handler(args: argparse.Namespace) -> WindowRequest:
    """
    CLI handler for launching the GONet GUI.

    This handler ensures that the unified UI server is running on the requested
    port and returns a :class:`~GONet_Wizard.commands.ui_bridge.WindowRequest`
    instructing the UI layer to open the main launcher window.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments. Expected to provide a ``port`` attribute
        specifying the UI server port.

    Returns
    -------
    :class:`~GONet_Wizard.commands.ui_bridge.WindowRequest`
        A request to open the GONet Launcher window.

    Raises
    ------
    :class:`RuntimeError`
        If the unified UI server cannot be started.
    """
    from GONet_Wizard.ui.runtime import ensure_server_running

    port = ensure_server_running(port=args.port)

    return WindowRequest(
        key="launcher",
        spec=WindowSpec(
            title="GONet Launcher",
            url=f"http://127.0.0.1:{port}/",
            width=1100,
            height=750,
        ),
    )
