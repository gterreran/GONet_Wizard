# GONet_Wizard/cli.py

"""
Entry Point for the GONet Wizard Command-Line Interface
=======================================================

This module provides the top-level driver for the GONet Wizard CLI. It defines
:func:`.main`, which is used both by ``python -m GONet_Wizard`` and by the
installed console script (as configured in ``pyproject.toml``).

Rather than manually constructing a static argparse command tree, this module
delegates parser construction to the declarative command registry in
:mod:`GONet_Wizard.commands` and the centralized parser builder in
:mod:`GONet_Wizard.commands.parser_builder` (re-exported via
:mod:`GONet_Wizard.commands.cli_core`). The full CLI hierarchy—including
top-level commands, their arguments, and any nested subcommands—is declared via
:class:`~GONet_Wizard.commands.specs.ParserSpec` and
:class:`~GONet_Wizard.commands.specs.CommandSpec` objects.

In addition to classic terminal execution, command handlers may return UI
results (published previews and/or window-open requests). Global flags such as
``--ui-port`` and ``--debug-webview`` configure the unified UI runtime used to
render HTML output and manage desktop windows.

Workflow
--------

1. A root :class:`argparse.ArgumentParser` is created with version support.
2. The full CLI hierarchy is dynamically constructed by calling
   :func:`~GONet_Wizard.commands.parser_builder.build_subparser`, which walks the
   command specification tree declared in :mod:`GONet_Wizard.commands`.
3. Command-line arguments are parsed into an :class:`argparse.Namespace`.
4. If a command handler has been attached (via ``set_defaults(handler=...)``),
   it is executed as ``args.handler(args)``.
5. If no command is provided, help text is shown.

The :func:`main` function accepts an optional ``argv`` parameter, allowing clean
unit testing without modifying ``sys.argv``. When ``argv`` is ``None``, the
function behaves like a standard command-line program and parses
``sys.argv[1:]`` automatically.

Branding
--------

At import time, :func:`GONet_Wizard._branding.patch_webview_start` is invoked to
ensure consistent desktop window branding (icons, titles, startup behavior)
across all pywebview-backed UI entry points.

Available Commands
------------------

- ``show`` (:mod:`GONet_Wizard.commands.show`) — Visualize GONet files by channel using Plotly.
- ``show_meta`` (:mod:`GONet_Wizard.commands.show_meta`) — Display file metadata as text or HTML.
- ``extract`` (:mod:`GONet_Wizard.commands.extract`) — Extract counts from GONet image files.
- ``dashboard`` (:mod:`GONet_Wizard.commands.run_dashboard`) — Launch the interactive dashboard.
- ``gui`` (:mod:`GONet_Wizard.commands.gui`) — Open the unified GUI launcher window.
- ``build_full_array`` (:mod:`GONet_Wizard.commands.build_full_array`) — Build/process full-array products.
- ``connect`` (:mod:`GONet_Wizard.commands.connect`) — Connect to a remote GONet camera via SSH.

  - ``snap`` (:mod:`GONet_Wizard.commands.connect_commands.snap`) — Trigger remote snapshot capture.
  - ``terminate_imaging`` (:mod:`GONet_Wizard.commands.connect_commands.terminate_imaging`) — Stop remote imaging processes.

"""

from __future__ import annotations
import argparse

from GONet_Wizard._version import __version__
from GONet_Wizard import commands
from GONet_Wizard.commands import cli_core
from GONet_Wizard._branding import patch_webview_start

patch_webview_start()

def main(argv=None) -> None:
    """
    Execute the GONet Wizard command-line interface.

    This function serves as the primary entry point for all CLI execution,
    whether invoked via the installed ``GONet_Wizard`` console script or through
    ``python -m GONet_Wizard``. It constructs the root argument parser, attaches
    global options (such as ``--version``), and delegates all command and
    subcommand registration to the centralized parser builder in
    :mod:`GONet_Wizard.commands.cli_core`.

    Parameters
    ----------
    argv : :class:`list` of :class:`str`, optional
        A list of command-line arguments to parse instead of ``sys.argv``.
        This is primarily intended for testing. When ``None`` (default), the
        function processes ``sys.argv[1:]`` automatically.

    Returns
    -------
    None
        This function does not return a value. It invokes command handlers for
        side effects, such as displaying images, launching dashboards, or
        performing remote SSH operations.

    """
    parser = argparse.ArgumentParser(
        description="GONet Wizard command-line interface."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GONet Wizard {__version__}",
    )

    parser.add_argument(
        "--ui-port",
        type=int,
        default=5050,
        help="Port for the unified local UI server (preview and GUI pages).",
    )
    
    parser.add_argument(
        "--debug-webview",
        action="store_true",
        default=False,
        help="Enable pywebview debug mode.",
    )
    parser = cli_core.build_subparser(parser, commands)
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return

    args.handler(args)
