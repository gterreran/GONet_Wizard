# GONet_Wizard/commands/show/io.py

"""
Show Export Utilities
=====================

This module provides export helpers for the :mod:`~GONet_Wizard.commands.show`
command, primarily for writing Plotly figures to disk.

The ``show`` command renders interactive HTML for viewing in a UI window, but it
also supports saving a static artifact (PDF) for sharing or archival. Static
exports are handled here to keep I/O and filesystem policy (extensions,
overwrite avoidance, error messaging) separate from figure construction.

Functions
---------
save_figure_plotly
    Export a Plotly figure to a PDF file, automatically adding the extension and
    avoiding overwrites by suffixing a counter.
"""

from __future__ import annotations

import os

import plotly.graph_objects as go


def save_figure_plotly(fig: go.Figure, save_path: str) -> str:
    """
    Export a Plotly figure to a PDF file, avoiding overwrites.

    If ``save_path`` does not end with ``.pdf``, the extension is appended. If a
    file already exists at that path, a numeric suffix (``_1``, ``_2``, ...)
    is added before the extension until an unused filename is found.

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
        :mod:`kaleido` dependency is not installed or cannot be invoked.
    """
    if not save_path.lower().endswith(".pdf"):
        save_path += ".pdf"

    base, ext = os.path.splitext(save_path)
    final_path = save_path
    counter = 1

    while os.path.exists(final_path):
        final_path = f"{base}_{counter}{ext}"
        counter += 1

    try:
        # Plotly static export requires the 'kaleido' engine.
        fig.write_image(final_path)
    except Exception as e:
        raise RuntimeError(
            "Failed to write PDF. Plotly static export requires 'kaleido'. "
            "Try: pip install -U kaleido"
        ) from e

    return final_path
