# GONet_Wizard/commands/show/io.py

"""
Show Export Utilities
=====================

This module provides export helpers for the :mod:`~GONet_Wizard.commands.show`
command, primarily for writing Plotly figures to disk.

The ``show`` command renders interactive HTML for viewing in a UI window, but it
also supports saving a static artifact for sharing or archival. Static exports
are handled here to keep I/O and filesystem policy (extensions, overwrite
avoidance, error messaging) separate from figure construction. HTML export is
also supported as a fast, self-contained alternative that does not require
Kaleido.

Functions
---------
save_figure_plotly
    Export a Plotly figure to PDF/PNG/SVG/JPEG/WEBP or self-contained HTML,
    automatically adding a default extension and avoiding overwrites by
    suffixing a counter.
"""

from __future__ import annotations

import os
from pathlib import Path

import plotly.graph_objects as go


_STATIC_EXPORT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".svg"}
_HTML_EXPORT_EXTENSIONS = {".html", ".htm"}
_DEFAULT_EXPORT_EXTENSION = ".pdf"


def _resolve_show_export_path(save_path: str) -> str:
    """Return a supported export path, adding a default suffix when missing."""
    path = str(save_path).strip()
    if not path:
        raise RuntimeError("No output path was selected.")

    suffix = Path(path).suffix.lower()
    if not suffix:
        path += _DEFAULT_EXPORT_EXTENSION
        suffix = _DEFAULT_EXPORT_EXTENSION

    if suffix not in _STATIC_EXPORT_EXTENSIONS | _HTML_EXPORT_EXTENSIONS:
        supported = ", ".join(sorted(_STATIC_EXPORT_EXTENSIONS | _HTML_EXPORT_EXTENSIONS))
        raise RuntimeError(f"Unsupported show export format {suffix!r}. Use one of: {supported}.")

    return path


def _avoid_overwrite(save_path: str) -> str:
    """Return a non-existing path by suffixing a counter when needed."""
    base, ext = os.path.splitext(save_path)
    final_path = save_path
    counter = 1

    while os.path.exists(final_path):
        final_path = f"{base}_{counter}{ext}"
        counter += 1

    return final_path


def save_figure_plotly(fig: go.Figure, save_path: str) -> str:
    """
    Export a Plotly figure, avoiding overwrites.

    If ``save_path`` has no extension, ``.pdf`` is appended. Static extensions
    ``.pdf``, ``.png``, ``.jpg``, ``.jpeg``, ``.webp``, and ``.svg`` are written
    with Plotly/Kaleido. ``.html`` and ``.htm`` are written as self-contained
    interactive HTML files and do not require Kaleido.

    Parameters
    ----------
    fig : :class:`plotly.graph_objects.Figure`
        Figure to export.
    save_path : :class:`str`
        Desired output path.

    Returns
    -------
    :class:`str`
        The final path written to disk.

    Raises
    ------
    :class:`RuntimeError`
        If Plotly static export fails. This commonly happens when the
        :mod:`kaleido` dependency or its browser backend is not available.
    """
    final_path = _avoid_overwrite(_resolve_show_export_path(save_path))
    suffix = Path(final_path).suffix.lower()

    try:
        if suffix in _HTML_EXPORT_EXTENSIONS:
            fig.write_html(final_path, include_plotlyjs=True, full_html=True)
        else:
            # Plotly static export requires the 'kaleido' engine.
            fig.write_image(final_path)
    except Exception as e:
        raise RuntimeError(
            "Failed to export the show figure. Static formats require Plotly/Kaleido "
            "and a working browser backend. For a fast export that avoids Kaleido, "
            "save with a .html extension."
        ) from e

    return final_path
