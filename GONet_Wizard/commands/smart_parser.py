# GONet_Wizard/commands/smart_parser.py

"""
Smart argparse Wrapper for Classified Parse Errors
==================================================

This module defines a custom :class:`argparse.ArgumentParser` subclass that
replaces argparse's default ``SystemExit``-based error handling with structured,
typed exceptions.

The parser classifies parse failures into broad categories (e.g. missing
required arguments vs. unknown arguments) and preserves contextual information
such as the original ``argv`` and the inferred command token sequence. This
enables higher-level CLI logic to decide how to handle parse failures, including
routing specific cases to GUI-backed workflows.

Constants
---------

:data:`_CURRENT_ARGV`
    Process-local copy of the current argument vector, used as a fallback for
    subparsers that are not explicitly initialized with an ``argv`` reference.

Functions
---------

:func:`.set_current_argv`
    Store the current argument vector for later retrieval during parse errors.

:func:`._guess_cmd_tokens`
    Extract a best-effort command token sequence from an argument vector.

Classes
-------

:class:`.SmartArgumentParser`
    Subclass of :class:`argparse.ArgumentParser` that raises
    :class:`~GONet_Wizard.commands.argparse_errors.CliParseError` instead of
    exiting the process.

"""

from __future__ import annotations

import argparse
from typing import Optional, Sequence

from GONet_Wizard.commands.argparse_errors import CliParseError, ParseErrorKind

_CURRENT_ARGV: list[str] = []


def set_current_argv(argv: Sequence[str]) -> None:
    """
    Store the current argument vector for parse-time error handling.

    This function records a process-local copy of ``argv`` so that subparsers
    created by argparse (which do not receive custom constructor arguments) can
    still access the full invocation context when reporting parse errors.

    Parameters
    ----------
    argv : :class:`~typing.Sequence` of :class:`str`
        Argument vector representing the current CLI invocation (typically
        ``sys.argv[1:]``).

    Returns
    -------
    None
        This function does not return a value.

    Raises
    ------
    None
    """
    global _CURRENT_ARGV
    _CURRENT_ARGV = list(argv)


def _guess_cmd_tokens(argv: Sequence[str]) -> list[str]:
    """
    Extract a command token sequence from an argument vector.

    Tokens are collected from the start of ``argv`` until an option-like token
    (beginning with ``"-"``) is encountered. The result represents a best-effort
    approximation of the intended command path.

    Parameters
    ----------
    argv : :class:`~typing.Sequence` of :class:`str`
        Argument vector to inspect.

    Returns
    -------
    list of str
        Ordered list of command tokens (e.g., ``["show"]`` or
        ``["connect", "snap"]``).

    Raises
    ------
    None
    """
    toks: list[str] = []
    for t in argv:
        if t.startswith("-"):
            break
        toks.append(t)
    return toks


class SmartArgumentParser(argparse.ArgumentParser):
    """
    Argument parser that raises structured exceptions on parse failure.

    This class overrides argparse's default error and exit behavior to raise
    :class:`~GONet_Wizard.commands.argparse_errors.CliParseError` instead of
    calling ``sys.exit``. Each error is classified into a
    :class:`~GONet_Wizard.commands.argparse_errors.ParseErrorKind` and includes
    contextual information about the original invocation.

    Attributes
    ----------
    _argv : :class:`~typing.Optional` of :class:`~typing.Sequence` of :class:`str`
        Argument vector explicitly associated with this parser instance, if
        provided at construction time.
    """

    def __init__(self, *args, argv: Optional[Sequence[str]] = None, **kwargs):
        """
        Initialize the smart argument parser.

        Parameters
        ----------
        *args
            Positional arguments forwarded to
            :class:`argparse.ArgumentParser`.
        argv : :class:`~typing.Optional` of :class:`~typing.Sequence` of
            :class:`str`, optional
            Argument vector to associate with this parser instance for error
            reporting.
        **kwargs
            Keyword arguments forwarded to
            :class:`argparse.ArgumentParser`.

        Returns
        -------
        None
        """
        super().__init__(*args, **kwargs)
        self._argv = list(argv) if argv is not None else None

    def _effective_argv(self) -> list[str]:
        """
        Return the argument vector to use for error reporting.

        If the parser instance was initialized with an explicit ``argv``, that
        value is used. Otherwise, the process-local fallback set via
        :func:`.set_current_argv` is returned.

        Returns
        -------
        list of str
            Argument vector associated with the current parse context.

        Raises
        ------
        None
        """
        return list(self._argv) if self._argv is not None else list(_CURRENT_ARGV)

    def error(self, message: str) -> None:
        """
        Handle an argparse parsing error.

        This method classifies the failure based on the error message and raises
        a :class:`~GONet_Wizard.commands.argparse_errors.CliParseError` containing
        the classification and contextual information.

        Parameters
        ----------
        message : :class:`str`
            Error message produced by argparse.

        Returns
        -------
        None

        Raises
        ------
        :class:`~GONet_Wizard.commands.argparse_errors.CliParseError`
            Always raised to signal a classified parse failure.
        """
        argv = self._effective_argv()
        cmd_tokens = _guess_cmd_tokens(argv)

        msg_l = (message or "").lower()
        if "the following arguments are required" in msg_l:
            kind = ParseErrorKind.MISSING_REQUIRED
        elif "unrecognized arguments:" in msg_l:
            kind = ParseErrorKind.UNKNOWN_ARGS
        else:
            kind = ParseErrorKind.OTHER

        raise CliParseError(
            kind=kind,
            message=message,
            argv=tuple(argv),
            cmd_tokens=tuple(cmd_tokens),
        )

    def exit(self, status: int = 0, message: Optional[str] = None) -> None:
        """
        Intercept argparse exit calls.

        This override ensures that any attempt by argparse to terminate the
        process results in a :class:`~GONet_Wizard.commands.argparse_errors.CliParseError`
        instead.

        Parameters
        ----------
        status : :class:`int`, optional
            Exit status requested by argparse.
        message : :class:`~typing.Optional` of :class:`str`, optional
            Optional message associated with the exit.

        Returns
        -------
        None

        Raises
        ------
        :class:`~GONet_Wizard.commands.argparse_errors.CliParseError`
            Always raised to prevent process termination.
        """
        argv = self._effective_argv()
        raise CliParseError(
            kind=ParseErrorKind.OTHER,
            message=message or "",
            argv=tuple(argv),
            cmd_tokens=tuple(_guess_cmd_tokens(argv)),
        )
