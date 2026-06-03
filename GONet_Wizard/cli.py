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

The CLI supports both terminal-only execution and UI-backed workflows:

- **Terminal mode**: the parsed command handler is executed directly.
- **UI-backed mode**: some handlers may return structured UI results
  (published previews and/or window-open requests), which are interpreted by the
  UI bridge and rendered through the unified local UI server and pywebview.

In addition, the CLI includes a parse-time routing behavior for command forms:
when a user invokes a valid command token sequence but omits required arguments,
the CLI can open the corresponding GUI form page (served by the unified UI
server) directly, bypassing the launcher hub page. This routing is triggered
only when the invocation contains *only* the command token sequence (after
removing global flags), so other parsing failures (unknown flags, malformed
options, etc.) continue to behave like a standard terminal CLI.

Global flags such as ``--ui-port`` and ``--debug-webview`` configure the unified
UI runtime used to render HTML output and manage desktop windows. These flags
are pre-parsed independently of the command tree so they can be applied even
when full argument parsing fails.

Workflow
--------

1. Determine the effective ``argv`` (from ``sys.argv[1:]`` or from the provided
   ``argv`` argument in tests).
2. Store the current ``argv`` for parse-time error reporting and subparser
   error classification (used by :class:`~GONet_Wizard.commands.smart_parser.SmartArgumentParser`).
3. Pre-parse global UI flags (``--ui-port``, ``--debug-webview``) without
   triggering subparser validation.
4. Construct the root parser using :class:`~GONet_Wizard.commands.smart_parser.SmartArgumentParser`,
   attach global CLI flags, and build the full command hierarchy via
   :func:`~GONet_Wizard.commands.parser_builder.build_subparser`.
5. Parse arguments into an :class:`argparse.Namespace`.

   - On successful parse, dispatch to the registered handler (``args.handler``).
   - On parse failure, classify the error and:

     - open a command form page for command-only invocations missing required
       arguments, or
     - print standard usage/error text for all other parse errors.

6. If no command was provided (no handler attached), show help.

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
import argparse, sys

from GONet_Wizard.commands.smart_parser import SmartArgumentParser, set_current_argv
from GONet_Wizard.commands.argparse_errors import CliParseError, ParseErrorKind
from GONet_Wizard._version import __version__
from GONet_Wizard import commands
from GONet_Wizard.commands import cli_core
from GONet_Wizard._branding import patch_webview_start
from GONet_Wizard.logging_utils import configure_logging
from typing import List, Optional, Tuple

patch_webview_start()

def _split_global_and_rest(argv: Optional[List[str]]) -> Tuple[argparse.Namespace, List[str]]:
    """
    Pre-parse global UI flags and return the remaining command tokens.

    This helper parses a small subset of process-level flags (currently
    ``--ui-port`` and ``--debug-webview``) using a minimal parser that does not
    register subcommands. The goal is to recover UI configuration reliably even
    when full command parsing fails (e.g., missing required arguments).

    The function uses :meth:`argparse.ArgumentParser.parse_known_args` so unknown
    tokens are preserved. The returned ``rest`` list contains the remaining
    tokens after global flags are consumed and is suitable for lightweight
    inspection (e.g., determining whether an invocation consisted only of a
    command token sequence).

    Parameters
    ----------
    argv : :class:`list` of :class:`str`, optional
        Argument vector to parse (typically ``sys.argv[1:]``). If ``None``,
        argparse treats it as an empty list.

    Returns
    -------
    tuple
        Two-tuple ``(globals_ns, rest)`` where:

        - ``globals_ns`` (:class:`argparse.Namespace`) contains parsed global
          options (e.g., ``ui_port``, ``debug_webview``).
        - ``rest`` (:class:`list` of :class:`str`) contains all remaining tokens
          not consumed by the global pre-parser (typically the command token
          sequence and any command-specific options/positionals).

    Raises
    ------
    None
        This function does not raise; it preserves unknown tokens in ``rest``.
    """

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--ui-port", type=int, default=5050)
    pre.add_argument("--debug-webview", action="store_true", default=False)
    pre.add_argument("--log-level", default=None)
    g, rest = pre.parse_known_args(argv)
    return g, rest


def _guess_cmd_tokens_from_rest(rest: list[str]) -> list[str]:
    """
    Extract the command token sequence from the argument list remaining after
    global flag pre-parsing.

    This helper scans the argument tokens that were *not* consumed by the
    global pre-parser (e.g. ``--ui-port``, ``--debug-webview``) and returns the
    leading contiguous sequence of non-option tokens. These tokens correspond
    to the command and any nested subcommand names (for example,
    ``["connect", "snap"]``).

    The extraction stops at the first token beginning with ``"-"``, ensuring
    that only command identifiers are returned and that option flags are
    excluded.

    Parameters
    ----------
    rest : :class:`list` of :class:`str`
        Remaining command-line tokens after global arguments have been parsed
        and removed.

    Returns
    -------
    :class:`list` of :class:`str`
        The ordered sequence of command tokens inferred from ``rest``. Returns
        an empty list if no command tokens can be identified.
    """
    
    toks: list[str] = []
    for t in rest:
        if t.startswith("-"):
            break
        toks.append(t)
    return toks


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

    actual_argv: List[str] = sys.argv[1:] if argv is None else list(argv)
    set_current_argv(actual_argv)

    globals_ns, rest = _split_global_and_rest(actual_argv)

    parser = SmartArgumentParser(
        description="GONet Wizard command-line interface.",
        argv=actual_argv,
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

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help=(
            "Enable package logging at the selected level. By default, only "
            "commands that explicitly configure logging emit log messages."
        ),
    )

    parser = cli_core.build_subparser(parser, commands)

    try:
        args = parser.parse_args(actual_argv)
    except CliParseError as e:
        # 1) if user typed a command but missed required positionals/required args -> open form
        cmd_tokens = _guess_cmd_tokens_from_rest(rest)

        if e.kind == ParseErrorKind.MISSING_REQUIRED and cmd_tokens and list(rest) == list(cmd_tokens):
            from GONet_Wizard.ui.launch_forms import open_command_form
            open_command_form(
                cmd_tokens=cmd_tokens,
                port=globals_ns.ui_port,
                debug_webview=globals_ns.debug_webview,
            )
            return

        # 2) otherwise: keep normal CLI behavior (error + help)
        # Match argparse UX: print usage + error line
        parser.print_usage()
        if e.message:
            parser._print_message(f"{parser.prog}: error: {e.message}\n")
        return

    if args.log_level is not None:
        configure_logging(args.log_level)

    if not hasattr(args, "handler"):
        parser.print_help()
        return

    args.handler(args)
