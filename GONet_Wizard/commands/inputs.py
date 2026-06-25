# GONet_Wizard/commands/inputs.py

"""
CLI Input Expansion and File Extension Filtering
================================================

This module provides reusable utilities for expanding command-line file inputs
into concrete filesystem paths. It supports common CLI input patterns including
single files, non-recursive directory expansion, glob patterns, and comma-separated
token lists, while preserving input order and removing duplicates.

These helpers are used primarily by :mod:`argparse`-based commands to normalize
user input before downstream processing (e.g., reading GONet files or JSON outputs).

Classes
-------
:class:`ExtensionFilterError`
    Exception raised when extension-based filtering yields no results.
:class:`ExpandFilenames`
    :class:`argparse.Action` that expands CLI tokens into a list of
    :class:`pathlib.Path` objects.

Functions
---------
:func:`expand_inputs`
    Expand file and directory tokens into a flat, de-duplicated list of paths.
:func:`filter_by_ext`
    Filter a list of paths by allowed file extensions.

"""

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
from typing import Iterable, List, Sequence


class ExtensionFilterError(ValueError):
    """
    Raised when extension-based filtering returns no files.

    This exception indicates that an extension allowlist was applied to a set of
    candidate paths but no paths matched.

    Notes
    -----
    This is a subclass of :class:`ValueError` to communicate invalid user input
    in CLI contexts.
    """


class ExpandFilenames(argparse.Action):
    """
    :class:`argparse.Action` to expand CLI filename tokens into concrete paths.

    This action normalizes user-provided input arguments that may include:

    - individual file paths
    - directories (non-recursive expansion)
    - wildcard patterns (e.g. ``*.tiff``)
    - comma-separated lists of the above

    The resolved paths are stored on the destination attribute as a
    :class:`list` of :class:`pathlib.Path`.

    Attributes
    ----------
    None
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Expand input tokens into a flat list of file paths.

        This method delegates to :func:`expand_inputs` and integrates with
        :mod:`argparse` error handling. If a token cannot be resolved to one or
        more existing files, the parser is instructed to exit with a
        user-facing error message.

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
        :class:`SystemExit`
            Raised indirectly by :meth:`argparse.ArgumentParser.error` if any
            input token does not match files.

        Notes
        -----
        :func:`expand_inputs` raises :class:`FileNotFoundError` for unmatched
        tokens; this action converts that into an :mod:`argparse` parse error.
        """
        try:
            files = expand_inputs(values)
        except FileNotFoundError as e:
            parser.error(str(e))

        setattr(namespace, self.dest, files)


def expand_inputs(tokens: Sequence[str]) -> List[Path]:
    """
    Expand input tokens into a flat list of file paths.

    Tokens may refer to explicit files, directories (expanded non-recursively),
    glob patterns, or comma-separated lists of these. The returned list preserves
    first-seen order while removing duplicates.

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
    :class:`list` of :class:`pathlib.Path`
        A flat list of expanded file paths as :class:`pathlib.Path` objects.

    Raises
    ------
    :class:`FileNotFoundError`
        If any token (or comma-separated sub-token) does not match one or more
        existing files.
    """
    out: List[Path] = []
    seen: set[Path] = set()

    def add_file(p: Path) -> None:
        """
        Add a path to the output list if it has not already been seen.

        Parameters
        ----------
        p : :class:`pathlib.Path`
            File path to normalize and append.

        Returns
        -------
        None
        """
        p = p.expanduser()
        if p not in seen:
            out.append(p)
            seen.add(p)

    for item in tokens:
        for part in str(item).split(","):
            part = part.strip()
            if not part:
                continue

            p = Path(os.path.expanduser(part))

            if p.is_file():
                add_file(p)
                continue

            if p.is_dir():
                for child in p.iterdir():
                    if child.is_file():
                        add_file(child)
                continue

            matches = [
                Path(m)
                for m in glob.glob(os.path.expanduser(part))
                if os.path.isfile(m)
            ]
            if matches:
                for m in matches:
                    add_file(m)
            else:
                raise FileNotFoundError(f"No files matched: {part!r}")

    return out


def filter_by_ext(paths: Sequence[Path], exts: Iterable[str]) -> List[Path]:
    """
    Filter a list of file paths by extension.

    This function normalizes the provided extension allowlist (case-insensitive,
    with or without leading dots) and returns the subset of paths whose
    :attr:`pathlib.Path.suffix` matches.

    Parameters
    ----------
    paths : :class:`list` of :class:`pathlib.Path`
        List of file paths to filter.
    exts : :class:`list` of :class:`str`
        List of allowed file extensions (with or without leading dot).
        Example: ``['.tiff', '.tif', '.json']``

    Returns
    -------
    :class:`list` of :class:`pathlib.Path`
        Filtered list of file paths that match the allowed extensions.

    Raises
    ------
    :class:`.ExtensionFilterError`
        If no files match the allowed extensions.
    """
    norm = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
    filtered: List[Path] = [p for p in paths if p.suffix.lower() in norm]

    if not filtered:
        raise ExtensionFilterError(
            f"No files matched required extension(s): {sorted(norm)}"
        )

    return filtered
