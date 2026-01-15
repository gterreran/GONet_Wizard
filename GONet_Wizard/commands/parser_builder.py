# GONet_Wizard/commands/parser_builder.py

"""
CLI Parser Construction Utilities
=================================

This module provides helper functions to build an :mod:`argparse` command tree
from declarative command and parser specifications. It supports both simple
leaf commands (no nested subcommands) and hierarchical command groups via
recursive subparser construction.

The resulting parsers are configured to dispatch to command handlers, with
handlers wrapped through :func:`~GONet_Wizard.commands.ui_bridge.wrap_handler_for_ui`
to enable consistent execution from both CLI and UI entry points.

Functions
---------
:func:`register_simple_subcommand`
    Register a single leaf command specification on a subparser group.
:func:`build_subparser`
    Recursively construct a parser and its nested subparsers from a package-defined
    :data:`PARSER` specification.

"""

from __future__ import annotations

import argparse
from typing import Any

from GONet_Wizard.commands.ui_bridge import wrap_handler_for_ui


def register_simple_subcommand(
    subparsers: argparse._SubParsersAction,
    cmd: Any,
) -> None:
    """
    Register a single simple command (no nested subparsers) to a subparser group.

    This function reads the :data:`COMMAND` specification from ``cmd`` to create
    a corresponding subparser, add its arguments, and attach a handler when the
    command exposes a ``cli_handler`` attribute.

    Parameters
    ----------
    subparsers : :class:`argparse._SubParsersAction`
        The subparser group to which the command parser will be added.
    cmd : :class:`object`
        A command module or object exposing a :data:`COMMAND` specification and
        optionally a ``cli_handler`` callable.

    Returns
    -------
    None

    Raises
    ------
    :class:`KeyError`
        If an argument specification declares ``"flags"`` but does not provide
        a valid sequence of flag strings.
    :class:`AttributeError`
        If ``cmd`` does not provide a :data:`COMMAND` attribute.
    """
    spec = cmd.COMMAND
    parser = subparsers.add_parser(spec.name, help=spec.help)

    for args in spec.args:
        if "flags" in args:
            flags = args["flags"]
            kwargs = {k: v for k, v in args.items() if k != "flags"}
            parser.add_argument(*flags, **kwargs)
        else:
            kwargs = {k: v for k, v in args.items()}
            parser.add_argument(**kwargs)

    if hasattr(cmd, "cli_handler"):
        parser.set_defaults(handler=wrap_handler_for_ui(cmd))


def build_subparser(parser: argparse.ArgumentParser, package) -> argparse.ArgumentParser:
    """
    Recursively build subparsers from a package defining a :data:`PARSER` object.

    This function attaches a subparser group to ``parser`` using the destination
    and help text defined by ``package.PARSER``. It then registers any leaf
    commands listed under ``package.PARSER.args["commands"]`` and recursively
    constructs nested subcommand groups from ``package.PARSER.args["subparsers"]``.

    Parameters
    ----------
    parser : :class:`argparse.ArgumentParser`
        The parser to augment with subparsers.
    package : :class:`object`
        A package-like object exposing a :data:`PARSER` specification describing
        available commands and nested parser groups.

    Returns
    -------
    :class:`argparse.ArgumentParser`
        The updated parser instance.

    Raises
    ------
    :class:`AttributeError`
        If ``package`` does not define a :data:`PARSER` attribute.
    :class:`KeyError`
        If a nested subparser specification references a ``parser_name`` that is
        not present in the current subparser group's ``choices``.
    """
    subparsers = parser.add_subparsers(dest=package.PARSER.dest, help=package.PARSER.help)

    if package.PARSER.args.get("commands"):
        for cmd in package.PARSER.args["commands"]:
            register_simple_subcommand(subparsers, cmd)

    if package.PARSER.args.get("subparsers"):
        for subpkg in package.PARSER.args["subparsers"]:
            build_subparser(subparsers.choices[subpkg["parser_name"]], subpkg["package"])

    return parser
