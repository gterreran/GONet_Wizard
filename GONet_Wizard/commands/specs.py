# GONet_Wizard/commands/specs.py

"""
Declarative CLI Specification Models
====================================

This module defines lightweight dataclass models used to describe the structure
of the GONet Wizard command-line interface in a declarative way. These
specifications are consumed by parser-construction utilities to build an
:class:`argparse.ArgumentParser` tree without duplicating argument wiring logic
across command modules.

Classes
-------
:class:`ParserSpec`
    Specification for a command group / subparser group (including nested groups).
:class:`CommandSpec`
    Specification for a single CLI command and its argument definitions.

"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParserSpec:
    """
    Declarative specification for an :mod:`argparse` subparser group.

    A :class:`ParserSpec` describes a command group (e.g., top-level commands or a
    nested group) by defining the destination name under which :mod:`argparse`
    stores the selected command, a help string, and a configuration dictionary
    describing available commands and nested parser groups.

    Attributes
    ----------
    dest : :class:`str`
        Attribute name under which :mod:`argparse` stores the chosen command.
    help : :class:`str`
        Help string for this subparser group.
    args : :class:`dict`
        Parser-group configuration. Common keys include:

        - ``"commands"``: iterable of command modules/objects (each exposing :data:`COMMAND`)
        - ``"subparsers"``: nested parser group specifications
    """
    dest: str
    help: str
    args: dict


@dataclass
class CommandSpec:
    """
    Declarative specification for a single CLI command.

    A :class:`CommandSpec` defines a command name, its help text, and a sequence
    of argument specifications that are passed through to
    :meth:`argparse.ArgumentParser.add_argument` during parser construction.

    Command modules typically expose a :data:`COMMAND` instance of this class and
    a ``cli_handler(args)`` function. Parser builders may attach the handler via
    ``set_defaults(handler=...)`` to enable dispatch after argument parsing.

    Attributes
    ----------
    name : :class:`str`
        Command name.
    help : :class:`str`
        Help string for the command.
    args : :class:`list` of :class:`dict`
        A list of :meth:`argparse.ArgumentParser.add_argument` specification
        dictionaries.
    """
    name: str
    help: str
    args: list
