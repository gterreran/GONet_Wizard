# GONet_Wizard/paths.py

"""
User-Writable Path Helpers
==========================

Installed desktop applications should treat their installation directory as
read-only.  This module provides small platform-aware helpers for paths that the
application may write to at runtime: cache files, logs, configuration files, and
user data.

The helpers avoid third-party dependencies so they can be used very early during
application startup and inside frozen bundles.  Tests and advanced users can set
``GONET_WIZARD_HOME`` to force all writable paths under a single directory.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Literal


APP_NAME = "GONet Wizard"
APP_SLUG = "gonet-wizard"
ENV_HOME = "GONET_WIZARD_HOME"
PathKind = Literal["data", "config", "cache", "logs", "temp"]


def _ensure(path: Path, *, create: bool) -> Path:
    """
    Optionally create a directory and return it.

    Parameters
    ----------
    path : pathlib.Path
        Directory path to return.
    create : bool
        If ``True``, create the directory and parents when missing.

    Returns
    -------
    pathlib.Path
        The original path.
    """
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _home_override(kind: PathKind) -> Path | None:
    """
    Return an override directory from ``GONET_WIZARD_HOME`` if configured.

    Parameters
    ----------
    kind : {"data", "config", "cache", "logs", "temp"}
        Writable path category.

    Returns
    -------
    pathlib.Path or None
        Override directory for the requested category, or ``None`` when the
        environment variable is not configured.
    """
    raw = os.environ.get(ENV_HOME)
    if not raw:
        return None
    base = Path(raw).expanduser()
    return base / kind


def _platform_base(kind: PathKind) -> Path:
    """
    Return the platform-specific base directory for one path category.

    Parameters
    ----------
    kind : {"data", "config", "cache", "logs", "temp"}
        Writable path category.

    Returns
    -------
    pathlib.Path
        Platform-appropriate base directory for GONet Wizard runtime files.
    """
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        if kind == "cache":
            return home / "Library" / "Caches" / APP_NAME
        if kind == "logs":
            return home / "Library" / "Logs" / APP_NAME
        if kind == "temp":
            return home / "Library" / "Caches" / APP_NAME / "TemporaryItems"
        return home / "Library" / "Application Support" / APP_NAME

    if system == "Windows":
        roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        if kind in {"cache", "logs", "temp"}:
            suffix = {
                "cache": "Cache",
                "logs": "Logs",
                "temp": "Temp",
            }[kind]
            return local / APP_NAME / suffix
        return roaming / APP_NAME

    # Linux and other Unix-like systems follow XDG defaults where possible.
    if kind == "cache":
        return Path(os.environ.get("XDG_CACHE_HOME", home / ".cache")) / APP_SLUG
    if kind == "config":
        return Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / APP_SLUG
    if kind == "logs":
        return Path(os.environ.get("XDG_STATE_HOME", home / ".local" / "state")) / APP_SLUG / "logs"
    if kind == "temp":
        return Path(os.environ.get("XDG_CACHE_HOME", home / ".cache")) / APP_SLUG / "tmp"
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / APP_SLUG


def user_dir(kind: PathKind, *parts: str | Path, create: bool = True) -> Path:
    """
    Return a user-writable application directory.

    Parameters
    ----------
    kind : {"data", "config", "cache", "logs", "temp"}
        Writable path category.
    *parts : str or pathlib.Path
        Optional child path segments below the category directory.
    create : bool, optional
        If ``True`` create the directory and parents. Defaults to ``True``.

    Returns
    -------
    pathlib.Path
        Platform-aware user-writable directory.
    """
    base = _home_override(kind) or _platform_base(kind)
    return _ensure(base.joinpath(*(str(p) for p in parts)), create=create)


def data_dir(*parts: str | Path, create: bool = True) -> Path:
    """Return a directory for persistent user data."""
    return user_dir("data", *parts, create=create)


def config_dir(*parts: str | Path, create: bool = True) -> Path:
    """Return a directory for user configuration files."""
    return user_dir("config", *parts, create=create)


def cache_dir(*parts: str | Path, create: bool = True) -> Path:
    """Return a directory for disposable application cache files."""
    return user_dir("cache", *parts, create=create)


def log_dir(*parts: str | Path, create: bool = True) -> Path:
    """Return a directory for application logs."""
    return user_dir("logs", *parts, create=create)


def temp_dir(*parts: str | Path, create: bool = True) -> Path:
    """Return a directory for temporary application files."""
    return user_dir("temp", *parts, create=create)


def config_file(*parts: str | Path, create_parent: bool = True) -> Path:
    """
    Return a path to a user configuration file.

    Parameters
    ----------
    *parts : str or pathlib.Path
        File path segments below the user configuration directory.
    create_parent : bool, optional
        If ``True`` create the parent directory. Defaults to ``True``.

    Returns
    -------
    pathlib.Path
        User-writable configuration file path.
    """
    path = config_dir(create=create_parent).joinpath(*(str(p) for p in parts))
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path
