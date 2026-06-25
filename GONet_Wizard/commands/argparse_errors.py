# GONet_Wizard/commands/argparse_errors.py

"""
CLI Parse Error Models
======================

This module defines small, typed models used to represent argument-parsing
failures without terminating the process.

The primary consumer is the CLI entry point, which can catch these exceptions
and choose between standard terminal error output and UI routing behavior.

Classes
-------

:class:`.ParseErrorKind`
    Enumeration describing broad categories of parse failures.

:class:`.CliParseError`
    Exception carrying a classified parse failure along with context such as the
    argv that triggered it and the best-effort extracted command token sequence.

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence


class ParseErrorKind(str, Enum):
    """
    Classification categories for CLI parsing failures.

    Attributes
    ----------
    MISSING_REQUIRED : :class:`str`
        A required argument was not provided (e.g., missing required positional).
    UNKNOWN_ARGS : :class:`str`
        One or more tokens were not recognized by the parser (e.g., unknown flag).
    OTHER : :class:`str`
        Any other parse failure that does not fall in the above categories.
    """

    MISSING_REQUIRED = "missing_required"
    UNKNOWN_ARGS = "unknown_args"
    OTHER = "other"


@dataclass
class CliParseError(Exception):
    """
    Exception raised to report a classified CLI parsing failure.

    This exception is intended to replace argparse's default ``SystemExit``-based
    error handling so callers can decide how to present failures (e.g., printing
    usage to stderr or opening a GUI form page).

    Attributes
    ----------
    kind : :class:`.ParseErrorKind`
        Classification of the parsing failure.
    message : :class:`str`
        Human-readable argparse error message associated with the failure.
    argv : :class:`~typing.Optional` of :class:`~typing.Sequence` of :class:`str`
        Argument vector that triggered the failure, if available.
    cmd_tokens : :class:`~typing.Optional` of :class:`~typing.Sequence` of :class:`str`
        Best-effort extracted command token sequence (e.g., ``("show",)`` or
        ``("connect", "snap")``), if available.
    """

    kind: ParseErrorKind
    message: str
    argv: Optional[Sequence[str]] = None
    cmd_tokens: Optional[Sequence[str]] = None

