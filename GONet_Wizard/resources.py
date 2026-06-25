# GONet_Wizard/resources.py

"""
Package Resource Location Helpers
=================================

This module centralizes filesystem access to resources shipped inside the
``GONet_Wizard`` Python package, such as static assets, HTML templates, icons,
and small data files.  The helpers are intentionally small wrappers around
:class:`pathlib.Path` because Flask, Dash, pywebview, and some scientific
libraries still expect real filesystem paths rather than abstract package
resources.

The same helpers are safe to use in three common execution modes:

- editable/source checkouts during development,
- normal wheel/sdist installations, and
- frozen desktop bundles created by tools such as PyInstaller.

For frozen applications, the code understands common PyInstaller data-file
layouts including ``_MEIPASS`` bundles, simple one-directory builds, and macOS
``.app`` bundles that store data under ``Contents/Resources``.  This keeps the
application code stable while the packaging specification is still evolving.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable


PACKAGE_NAME = "GONet_Wizard"


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    """
    Return paths in order, removing duplicate string representations.

    Parameters
    ----------
    paths : iterable of pathlib.Path
        Candidate paths to de-duplicate.

    Returns
    -------
    list of pathlib.Path
        Unique paths preserving the first occurrence of each candidate.
    """
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _pyinstaller_roots() -> list[Path]:
    """
    Return possible package roots inside a frozen PyInstaller bundle.

    Returns
    -------
    list of pathlib.Path
        Candidate directories ordered from most package-like to most generic.
        The list is empty when the process is not running from a frozen bundle.

    Notes
    -----
    PyInstaller may place collected data files under different roots depending
    on platform and build mode.  The common layouts are covered here:

    - ``sys._MEIPASS/GONet_Wizard`` and ``sys._MEIPASS`` for one-file and
      modern one-dir bundles;
    - ``<exe_dir>/GONet_Wizard`` and ``<exe_dir>`` for simple one-dir builds;
    - ``Contents/Resources/GONet_Wizard`` and ``Contents/Resources`` for macOS
      ``.app`` bundles.
    """
    if not getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None) is None:
        return []

    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        root = Path(meipass)
        candidates.extend([root / PACKAGE_NAME, root])

    executable = getattr(sys, "executable", None)
    if executable:
        exe_dir = Path(executable).resolve().parent
        candidates.extend([exe_dir / PACKAGE_NAME, exe_dir])

        # PyInstaller macOS app bundles usually execute from
        # GONet Wizard.app/Contents/MacOS while data files live under
        # GONet Wizard.app/Contents/Resources.
        if exe_dir.name == "MacOS" and exe_dir.parent.name == "Contents":
            resources_dir = exe_dir.parent / "Resources"
            candidates.extend([resources_dir / PACKAGE_NAME, resources_dir])

    return _dedupe_paths(candidates)


def _source_package_root() -> Path:
    """
    Return the package root for source/editable/installed execution.

    Returns
    -------
    pathlib.Path
        Directory containing this module, i.e. the ``GONet_Wizard`` package
        directory.
    """
    return Path(__file__).resolve().parent


def package_root() -> Path:
    """
    Return the best filesystem root for package-shipped resources.

    Returns
    -------
    pathlib.Path
        Directory that should contain package resources such as ``static`` and
        ``gui/templates``.
    """
    for candidate in _pyinstaller_roots():
        if (candidate / "static").exists() or (candidate / "gui" / "templates").exists():
            return candidate
    return _source_package_root()


def resource_path(*parts: str | Path, must_exist: bool = False) -> Path:
    """
    Build an absolute path to a package-shipped resource.

    Parameters
    ----------
    *parts : str or pathlib.Path
        Path segments relative to the package resource root. With no parts, the
        package resource root itself is returned.
    must_exist : bool, optional
        If ``True``, raise :class:`FileNotFoundError` when the resolved path does
        not exist. Defaults to ``False``.

    Returns
    -------
    pathlib.Path
        Absolute filesystem path to the requested resource.

    Raises
    ------
    FileNotFoundError
        If ``must_exist`` is ``True`` and the resource cannot be found.
    """
    rel_parts = tuple(str(p) for p in parts)
    candidates: Iterable[Path]

    pyinstaller_roots = _pyinstaller_roots()
    if pyinstaller_roots:
        candidates = [root.joinpath(*rel_parts) for root in pyinstaller_roots]
    else:
        candidates = [package_root().joinpath(*rel_parts)]

    candidates = list(candidates)
    for candidate in candidates:
        if candidate.exists():
            return candidate

    fallback = candidates[0]
    if must_exist:
        searched = ", ".join(str(p) for p in candidates)
        raise FileNotFoundError(f"Package resource not found: {searched}")
    return fallback


def static_dir(*parts: str | Path, must_exist: bool = False) -> Path:
    """
    Return a path inside the shared ``static`` resource directory.

    Parameters
    ----------
    *parts : str or pathlib.Path
        Optional path segments below ``static``.
    must_exist : bool, optional
        If ``True``, require the path to exist.

    Returns
    -------
    pathlib.Path
        Absolute path to the static directory or one of its children.
    """
    return resource_path("static", *parts, must_exist=must_exist)


def template_dir(*parts: str | Path, must_exist: bool = False) -> Path:
    """
    Return a path inside the Flask/Jinja template directory.

    Parameters
    ----------
    *parts : str or pathlib.Path
        Optional path segments below ``gui/templates``.
    must_exist : bool, optional
        If ``True``, require the path to exist.

    Returns
    -------
    pathlib.Path
        Absolute path to the template directory or one of its children.
    """
    return resource_path("gui", "templates", *parts, must_exist=must_exist)


def data_file(*parts: str | Path, must_exist: bool = False) -> Path:
    """
    Return a path inside the package-shipped GONet utility data directory.

    Parameters
    ----------
    *parts : str or pathlib.Path
        Optional path segments below ``GONet_utils/src``.
    must_exist : bool, optional
        If ``True``, require the path to exist.

    Returns
    -------
    pathlib.Path
        Absolute path to a package data file or directory.
    """
    return resource_path("GONet_utils", "src", *parts, must_exist=must_exist)


def logo_path(filename: str, *, must_exist: bool = False) -> Path:
    """
    Return a path to a logo/icon file shipped with the package.

    Parameters
    ----------
    filename : str
        Logo filename under ``static/img/logo``.
    must_exist : bool, optional
        If ``True``, require the icon file to exist.

    Returns
    -------
    pathlib.Path
        Absolute path to the requested logo file.
    """
    return static_dir("img", "logo", filename, must_exist=must_exist)
