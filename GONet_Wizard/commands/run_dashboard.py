# GONet_Wizard/commands/run_dashboard.py

"""
GONet Dashboard Launcher Command
================================

This module defines the ``dashboard`` CLI command used to launch the interactive
GONet Wizard dashboard. The command prepares and validates input data paths,
starts (or reuses) a Dash server instance, and requests that the dashboard be
opened in a managed UI window.

Input paths may refer to directories or individual files and are expanded using
shared CLI utilities. Only supported data formats are forwarded to the
dashboard backend.

The command is declared via the :data:`COMMAND` specification and dispatched
through :func:`cli_handler`, which returns a
:class:`~GONet_Wizard.commands.ui_bridge.WindowRequest` for UI presentation.

Constants
---------
:class:`COMMAND`
    :class:`~GONet_Wizard.commands.specs.CommandSpec` defining the ``dashboard``
    command and its CLI arguments.

Functions
---------
:func:`cli_handler`
    CLI entry point that prepares inputs, starts the dashboard server, and
    opens the dashboard window.

"""

from __future__ import annotations

import argparse

from GONet_Wizard import settings
from GONet_Wizard.GONet_dashboard.src.app import ensure_dashboard_running
from GONet_Wizard.commands.cli_core import (
    ExpandFilenames,
    CommandSpec,
    expand_inputs,
    filter_by_ext,
)
from GONet_Wizard.commands.ui_bridge import WindowRequest
from GONet_Wizard.ui.windows import WindowSpec


COMMAND = CommandSpec(
    name="dashboard",
    help="Launch the interactive GONet dashboard.",
    args=[
        {
            "flags": ["input"],
            "nargs": "+",
            "action": ExpandFilenames,
            "help": "Path to GONet data directory or JSON/CSV file(s). Default is current directory.",
        },
        {
            "flags": ["--debug"],
            "action": "store_true",
            "default": settings.DASHBOARD_DEBUG.default,
            "help": "Run the dashboard in debug mode (more verbose logging).",
        },
        {
            "flags": ["--port"],
            "type": int,
            "default": 8050,
            "help": "Port for the Dash server.",
        },
    ],
)


def cli_handler(args: argparse.Namespace):
    """
    CLI handler for launching the GONet dashboard.

    This handler expands and normalizes input paths, filters supported data
    files, ensures that the dashboard server is running, and returns a
    :class:`~GONet_Wizard.commands.ui_bridge.WindowRequest` instructing the UI
    layer to open the dashboard window.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments. Expected attributes include ``input``,
        ``debug``, and ``port``.

    Returns
    -------
    :class:`~GONet_Wizard.commands.ui_bridge.WindowRequest`
        A request to open the GONet Wizard Dashboard window.

    Raises
    ------
    :class:`.ExtensionFilterError`
        If no input files match the supported extensions.
    :class:`RuntimeError`
        If the dashboard server cannot be started.
    """
    # Expand/normalize inputs
    if not getattr(args, "input", None):
        inputs = expand_inputs(["."])
    else:
        inputs = expand_inputs(args.input)

    inputs = filter_by_ext(inputs, [".json", ".csv"])

    url = ensure_dashboard_running(
        input_files=[str(p) for p in inputs],
        debug=bool(args.debug),
        port=int(args.port),
    )

    # Return a WindowRequest so cli_core decides when to start the webview loop.
    return WindowRequest(
        key="dashboard",
        spec=WindowSpec(
            title="GONet Wizard Dashboard",
            url=url,
            width=1250,
            height=700,
        ),
    )
