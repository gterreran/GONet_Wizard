# GONet_Wizard/gui/web.py

"""
Flask Routes for the GONet Wizard GUI Forms
===========================================

This module defines the Flask blueprint powering the HTML form-based GUI used
by the GONet Wizard unified UI server. It serves:

- a landing page listing available commands,
- per-command form pages rendered from Jinja templates, and
- a JSON endpoint that executes CLI commands from GUI-submitted payloads.

The GUI is intentionally built on top of the existing CLI infrastructure. Form
submissions are converted into an ``argv`` list using argparse metadata, parsed
through the same command tree as the terminal CLI, and dispatched through the
registered command handler. This keeps the command logic centralized and avoids
duplicating behavior between CLI and GUI entry points.

To prevent circular import issues (commands importing UI helpers, while the UI
needs the command registry), the argparse parser is constructed lazily on first
use and cached for subsequent requests.

Constants
---------
:data:`launcher_bp` : :class:`flask.Blueprint`
    Flask blueprint registering the GUI routes.

Functions
---------
:func:`get_cli_parser`
    Lazily build and cache the CLI parser used to interpret GUI payloads.
:func:`index`
    Render the GUI landing page.
:func:`command_page`
    Render the form page for a specific command.
:func:`run_command`
    Execute a command using a GUI JSON payload.
:func:`payload_to_argv_with_parser`
    Convert a GUI payload dictionary into an ``argv`` list using argparse metadata.

"""

from __future__ import annotations

import argparse
from typing import Any, Optional

from flask import Blueprint, render_template, request, jsonify

from GONet_Wizard import commands as commands_pkg
from GONet_Wizard.commands import cli_core


launcher_bp = Blueprint("launcher", __name__)


# ----------------------------
# Lazy CLI parser construction
# ----------------------------

_CLI_PARSER: Optional[argparse.ArgumentParser] = None


def get_cli_parser() -> argparse.ArgumentParser:
    """
    Lazily build and cache the CLI parser.

    Building the parser walks the command specification tree and imports command
    modules. This can trigger circular imports if done at module import time, so
    the parser is constructed on first use and cached.

    Returns
    -------
    :class:`argparse.ArgumentParser`
        CLI parser including all registered subcommands.
    """
    global _CLI_PARSER
    if _CLI_PARSER is None:
        parser = argparse.ArgumentParser(description="GONet Wizard command-line interface.")
        _CLI_PARSER = cli_core.build_subparser(parser, commands_pkg)
    return _CLI_PARSER


# ----------------------------
# Routes
# ----------------------------

@launcher_bp.get("/")
def index():
    """
    Render the GUI landing page.

    Returns
    -------
    :class:`str`
        Rendered HTML for the index page.
    """
    return render_template("index.html")


@launcher_bp.get("/cmd/<cmd>")
def command_page(cmd: str):
    """
    Render the form page for a specific command.

    Parameters
    ----------
    cmd : :class:`str`
        Command name token (e.g. ``"show"`` or ``"dashboard"``).

    Returns
    -------
    :class:`str`
        Rendered HTML for the command form page.
    """
    form_path = f"forms/{cmd}.html"
    try:
        return render_template("form_page.html", form_template=form_path, command_name=cmd)
    except Exception:
        return f"<p>Unknown command: {cmd}</p>"


@launcher_bp.post("/run")
def run_command():
    """
    Run a CLI command from a GUI JSON payload.

    The request payload is converted to an ``argv`` list using argparse metadata
    (positionals vs options), parsed through the shared CLI parser, and executed
    via ``args.handler(args)``.

    Returns
    -------
    :class:`flask.Response`
        JSON response describing success or error, optionally including an HTML
        output string when returned by the command handler.

    Raises
    ------
    RuntimeError
        If the parser cannot be constructed or command execution fails.
    """
    payload = request.get_json() or {}

    try:
        parser = get_cli_parser()
        argv = payload_to_argv_with_parser(parser, dict(payload))  # copy
        if not argv:
            return jsonify({"status": "error", "message": "No command provided."})

        args = parser.parse_args(argv)

        if not hasattr(args, "handler"):
            return jsonify({"status": "error", "message": "No handler found for command."})

        result = args.handler(args)

        resp = {"status": "success", "message": f"Executed: {' '.join(argv)}"}
        if isinstance(result, str) and result.strip():
            resp["output"] = result

        return jsonify(resp)

    except SystemExit:
        return jsonify(
            {"status": "error", "message": "Invalid arguments. Please check your inputs."}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ----------------------------
# Payload -> argv conversion
# ----------------------------

def _truthy(v: Any) -> bool:
    """
    Interpret common GUI boolean representations.

    Parameters
    ----------
    v : :class:`object`
        Value from a GUI payload.

    Returns
    -------
    :class:`bool`
        ``True`` if the value resembles a truthy checkbox-like value.
    """
    if v is True:
        return True
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "on", "yes", "y"}
    return False


def _split_csv_tokens(s: str) -> list[str]:
    """
    Split a comma-separated string into CLI tokens.

    Parameters
    ----------
    s : :class:`str`
        Comma-separated token string.

    Returns
    -------
    :class:`list` of :class:`str`
        Non-empty, stripped tokens.
    """
    return [p.strip() for p in s.split(",") if p.strip()]


def _get_final_subparser(root: argparse.ArgumentParser, cmd_tokens: list[str]) -> argparse.ArgumentParser:
    """
    Resolve the final argparse subparser for a command token sequence.

    Parameters
    ----------
    root : :class:`argparse.ArgumentParser`
        Root parser containing the command tree.
    cmd_tokens : :class:`list` of :class:`str`
        Command token sequence (e.g. ``["connect", "snap"]``).

    Returns
    -------
    :class:`argparse.ArgumentParser`
        The most specific subparser that can be reached by walking ``cmd_tokens``.

    Notes
    -----
    If a token does not correspond to a known subparser choice, traversal stops
    and the current parser is returned.
    """
    parser = root
    for tok in cmd_tokens:
        sp_action = next(
            (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)),
            None,
        )
        if sp_action is None:
            break
        if tok not in sp_action.choices:
            break
        parser = sp_action.choices[tok]
    return parser


def payload_to_argv_with_parser(root: argparse.ArgumentParser, payload: dict) -> list[str]:
    """
    Convert a GUI payload into an ``argv`` list using argparse metadata.

    The conversion uses the destination names and action ordering from the final
    command parser to place positional arguments first and options afterward.

    Parameters
    ----------
    root : :class:`argparse.ArgumentParser`
        Root parser containing the full command tree.
    payload : :class:`dict`
        GUI payload containing:

        - ``command``: command token string (e.g. ``"show"`` or ``"extract"``)
        - additional form fields keyed by argparse dest name

    Returns
    -------
    :class:`list` of :class:`str`
        Token list suitable for :meth:`argparse.ArgumentParser.parse_args`.

    Notes
    -----
    - Positionals with multi-value ``nargs`` are commonly provided as a single
      comma-separated string by the GUI; these values are split into tokens.
    - Boolean checkbox fields are treated as ``store_true`` flags and only emit
      the option flag when truthy.
    """
    cmd = payload.pop("command", None)
    if not cmd:
        return []

    cmd_tokens = str(cmd).split()
    cmd_parser = _get_final_subparser(root, cmd_tokens)

    positional_actions = [
        a
        for a in cmd_parser._actions
        if getattr(a, "option_strings", None) == [] and a.dest != "help"
    ]
    positional_dests = [a.dest for a in positional_actions]

    argv: list[str] = []
    argv += cmd_tokens

    # 1) add positionals in order
    for dest in positional_dests:
        if dest not in payload:
            continue
        val = payload.pop(dest)

        if isinstance(val, str):
            argv += _split_csv_tokens(val)
        elif isinstance(val, list):
            for item in val:
                argv += _split_csv_tokens(str(item))
        else:
            argv.append(str(val))

    # 2) add options (everything remaining in payload)
    for key, val in payload.items():
        if val is None or val == "":
            continue

        flag = f"--{key.replace('_', '-')}"  # matches argparse flags

        # Boolean flags
        if isinstance(val, bool) or (
            isinstance(val, str)
            and val.strip().lower()
            in {"on", "true", "false", "1", "0", "yes", "no", "y", "n"}
        ):
            if _truthy(val):
                argv.append(flag)
            continue

        # Lists become repeated positional tokens
        if isinstance(val, list):
            argv.append(flag)
            argv.extend(str(v) for v in val)
            continue

        # Everything else is passed literally
        argv.append(flag)
        argv.append(str(val))

    return argv
