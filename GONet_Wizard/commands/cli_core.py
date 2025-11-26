"""
Core Utilities for the GONet Wizard Command-Line Interface
==========================================================

This module implements the declarative specification system used to construct
the entire GONet Wizard command-line interface. Rather than hand-writing a
large, nested argparse tree, the CLI is defined using lightweight dataclasses
(:class:`ParserSpec` and :class:`CommandSpec`) that describe command groups and
individual commands. The centralized parser builder then walks these
specifications recursively to create the full argparse hierarchy. 

This architecture keeps command modules simple, predictable, and highly
maintainable as the CLI grows.

Classes
-------
- :class:`ParserSpec` : Describes a single command's name, help, and arguments.
- :class:`CommandSpec` : Describes a group of commands and nested subparsers.
- :class:`ExtensionFilterError` : Exception for extension filtering errors.
- :class:`ExpandFilenames` : Argparse action for expanding filename inputs.

Functions
---------
- :func:`expand_inputs` : Expands filenames from various input formats.
- :func:`filter_by_ext` : Filters a list of file paths by allowed extensions.
- :func:`build_subparser` : Recursively builds subparsers from a package spec.
- :func:`_register_simple_subcommand` : Registers a single command to a subparser group.

"""

import argparse, os, glob
from typing import List, Sequence, Iterable, Any
from dataclasses import dataclass


@dataclass
class ParserSpec:
    """
    Describes a *single* command (e.g. ``show``, ``extract``), including:
      - the command name
      - its help text
      - a list of argument specifications to be passed to ``add_argument``

    Each command module exposes a ``COMMAND`` instance of this class together
    with a ``cli_handler(args)`` function, which is set as the dispatch handler
    for that command.
    
    Attributes
    ----------
    ----------
    name : :class:`str`
    help : :class:`str`
    args : :class:`list` of :class:`dict`
    """
    dest: str
    help: str
    args: dict


@dataclass
class CommandSpec:
    """
    Describes a *group of commands* and optionally nested groups. Each
    :class:`ParserSpec` defines:
      - a ``dest`` (the attribute under which argparse stores the chosen command)
      - a help string
      - a configuration dictionary that may contain:
          - ``commands`` — a list of :class:`CommandSpec` objects
          - ``subparsers`` — nested parser groups, each mapping a subcommand name
            to another package providing its own :class:`ParserSpec`

    This allows multi-level command trees such as:

        GONet_Wizard connect SNAP
        GONet_Wizard connect TERMINATE
    
    Attributes
    ----------
    name: :class:`str`
    help: :class:`str`
    args: :class:`list`

    """
    name: str
    help: str
    args: list

class ExtensionFilterError(ValueError):
    """Raised when extension-based filtering returns no files."""

class ExpandFilenames(argparse.Action):
    """
    Argparse action to expand filenames from various input formats.
    This action processes input arguments that may include:

      - individual file paths
      - directories (non-recursive expansion)
      - wildcard patterns (e.g. ``*.tiff``)
      - comma-separated lists of the above
    
    """
    def __call__(self, parser, namespace, values, option_string=None):
        """
        Expand input tokens into a flat list of file paths.
        
        Parameters
        ----------
        parser : :class:`argparse.ArgumentParser`
            The parser instance.
        namespace : :class:`argparse.Namespace`
            The namespace to which the expanded files will be added.
        values : :class:`list` of :class:`str`
            The input tokens to expand.
        option_string : :class:`str`, optional
            The option string used (if any).
        
        Returns
        -------
        None

        Raises
        ------
        :class:`FileNotFoundError`
            If any input token does not match files.

        """
        try:
            files = expand_inputs(values)
        except FileNotFoundError as e:
            parser.error(str(e))
        setattr(namespace, self.dest, files)

def expand_inputs(tokens):
    """
    Expand input tokens into a flat list of file paths.

    Parameters
    ----------
    tokens : :class:`list` of :class:`str`
        Input tokens that may include:

          - individual file paths
          - directories (non-recursive expansion)
          - wildcard patterns (e.g. ``*.tiff``)
          - comma-separated lists of the above
    
    Returns
    -------
    :class:`list` of :class:`str`
        A flat list of expanded file paths.
    
    Raises
    ------
    :class:`FileNotFoundError`
        If any input token does not match files.

    """
    out, seen = [], set()

    def add_file(p):
        if p not in seen:
            out.append(p); seen.add(p)

    for item in tokens:
        for part in str(item).split(','):
            part = part.strip()
            if not part:
                continue

            if os.path.isfile(part):
                add_file(part)
                continue

            if os.path.isdir(part):
                for name in os.listdir(part):       # non-recursive
                    p = os.path.join(part, name)
                    if os.path.isfile(p):
                        add_file(p)
                continue

            matches = [m for m in glob.glob(part) if os.path.isfile(m)]
            if matches:
                for m in matches:
                    add_file(m)
            else:
                # you can parser.error here instead if you prefer hard fail
                raise FileNotFoundError(f"No files matched: {part!r}")
            
    return out


def filter_by_ext(paths: Sequence[str], exts: Iterable[str]) -> List[str]:
    """
    Filter a list of file paths by extension.

    Parameters
    ----------
    paths : :class:`list` of :class:`str`
        List of file paths to filter.
    exts : :class:`list` of :class:`str`
        List of allowed file extensions (with or without leading dot).
        Example: ['.tiff', '.tif', '.json']
    
    Returns
    -------
    :class:`list` of :class:`str`
        Filtered list of file paths that match the allowed extensions.

    Raises
    ------
    :class:`.ExtensionFilterError`
        If `require_non_empty` is True and no files match the allowed extensions.

    """
    # normalize to lowercase with leading dot
    norm = {e.lower() if e.startswith('.') else f".{e.lower()}" for e in exts}

    filtered = [p for p in paths if os.path.splitext(p)[1].lower() in norm]

    if not filtered:
        raise ExtensionFilterError(f"No files matched required extension(s): {sorted(norm)}")

    return filtered

def _register_simple_subcommand(
        subparsers: argparse._SubParsersAction,
        cmd: Any,
    ) -> None:
    """
    Register a single simple command (no nested subparsers) to a subparser group.

    The function reads the :class:`CommandSpec` from the command module, adds the
    command to the provided ``subparsers`` group, and attaches the command's
    ``cli_handler`` function as the dispatch handler.

    Parameters
    ----------
    subparsers : :class:`argparse._SubParsersAction`
        The subparser group to which the command will be added.
    cmd : :mod:`module`
        The command module defining a :data:`COMMAND` and a ``cli_handler``.

    Returns
    -------
    None

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

    # unify dispatch key name, e.g. "handler"
    if hasattr(cmd, 'cli_handler'):
        parser.set_defaults(handler=cmd.cli_handler)


def build_subparser(parser: argparse.ArgumentParser, package) -> argparse.ArgumentParser:
    """
    Recursively build subparsers from a package defining a :data:`PARSER` object
    specification.

    The function is the core of this module. Given a root
    parser and a package providing a :class:`ParserSpec`, it:

    1. Creates a subparser group using the ``dest`` and ``help`` from the spec.
    2. Registers each simple command via :func:`_register_simple_subcommand`.
    3. Recursively handles nested parser groups defined under ``subparsers``.

    During registration, each command's ``cli_handler`` is attached via
    ``set_defaults(handler=...)``. At runtime, the main CLI driver simply executes:

        ``args.handler(args)``

    thus cleanly decoupling argument parsing from command implementation.

    Parameters
    ----------
    parser : :class:`argparse.ArgumentParser`
        The parent parser to which subparsers will be added.
    package : :mod:`module`
        A package defining a :data:`PARSER` object.

    Returns
    -------
    :class:`argparse.ArgumentParser`
        The modified parser with subparsers added.
    
    """
    subparsers = parser.add_subparsers(dest=package.PARSER.dest, help=package.PARSER.help)
    if package.PARSER.args.get('commands'):
        for cmd in package.PARSER.args['commands']:
            _register_simple_subcommand(subparsers, cmd)
    if package.PARSER.args.get('subparsers'):
        for subpkg in package.PARSER.args['subparsers']:
            build_subparser(subparsers.choices[subpkg['parser_name']], subpkg['package'])

    return parser