"""
Logging Utilities
=================

Small helpers for package-wide logging.

The package emits logs under the ``GONet_Wizard`` logger namespace. Library
modules should create module loggers with :func:`get_logger` and should not
configure handlers directly. CLI entry points may call :func:`configure_logging`
to make package logs visible to terminal users.
"""

from __future__ import annotations

import logging
from typing import Optional

PACKAGE_LOGGER_NAME = "GONet_Wizard"
DEFAULT_LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


# Libraries should not configure the root logger. A NullHandler prevents
# "No handler found" warnings while allowing applications to opt in.
logging.getLogger(PACKAGE_LOGGER_NAME).addHandler(logging.NullHandler())


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a logger in the package namespace.

    Parameters
    ----------
    name : :class:`str`, optional
        Module or component name. If the name already starts with
        ``"GONet_Wizard"``, it is used as-is. Otherwise it is appended to the
        package logger namespace.

    Returns
    -------
    :class:`logging.Logger`
        The requested package logger.
    """
    if not name:
        return logging.getLogger(PACKAGE_LOGGER_NAME)

    if name == PACKAGE_LOGGER_NAME or name.startswith(f"{PACKAGE_LOGGER_NAME}."):
        return logging.getLogger(name)

    return logging.getLogger(f"{PACKAGE_LOGGER_NAME}.{name}")


def configure_logging(
    level: int | str = logging.WARNING,
    *,
    force: bool = False,
    fmt: str = DEFAULT_LOG_FORMAT,
) -> None:
    """
    Configure terminal logging for GONet Wizard entry points.

    This function is intended for CLI/UI launchers, not low-level library code.
    It attaches a stream handler to the package logger if one is not already
    present and sets the package logger level.

    Parameters
    ----------
    level : :class:`int` or :class:`str`, optional
        Logging threshold. String values such as ``"INFO"`` and ``"DEBUG"`` are
        accepted. Defaults to :data:`logging.WARNING`.
    force : :class:`bool`, optional
        If ``True``, remove existing package logger handlers before installing a
        fresh stream handler. Defaults to ``False``.
    fmt : :class:`str`, optional
        Logging format string.

    Returns
    -------
    None
    """
    if isinstance(level, str):
        normalized = level.upper()
        if not hasattr(logging, normalized):
            raise ValueError(f"Unknown logging level: {level!r}")
        level = int(getattr(logging, normalized))

    logger = logging.getLogger(PACKAGE_LOGGER_NAME)

    if force:
        logger.handlers.clear()

    has_stream_handler = any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)
    if not has_stream_handler:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False


def silence_noisy_loggers(level: int = logging.ERROR) -> None:
    """
    Raise the threshold for noisy third-party web-server loggers.

    Parameters
    ----------
    level : :class:`int`, optional
        Logging level to apply to known noisy loggers. Defaults to
        :data:`logging.ERROR`.

    Returns
    -------
    None
    """
    for name in ("werkzeug", "dash.dash"):
        logging.getLogger(name).setLevel(level)
