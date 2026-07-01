# GONet_Wizard/commands/show/io.py

"""
Show Export Utilities
=====================

This module provides export helpers for the :mod:`~GONet_Wizard.commands.show`
command, primarily for writing the interactive show figure to disk.

The ``show`` command renders interactive HTML for viewing in a UI window, but it
also supports saving an artifact for sharing or archival. HTML export preserves
the full interactive Plotly figure. Static exports are rendered with Matplotlib
from the figure's heatmap data so packaged desktop apps do not depend on
Kaleido/Chrome being available at runtime.

Functions
---------
save_figure_plotly
    Export a Plotly figure to PDF/PNG/SVG/JPEG or self-contained HTML,
    automatically adding a default extension and avoiding overwrites by
    suffixing a counter.
"""

from __future__ import annotations

import math
import os
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go


_STATIC_EXPORT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".svg"}
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


def _show_meta(fig: go.Figure) -> dict[str, Any]:
    """Return the ``show`` metadata dictionary stored on a figure."""
    meta = getattr(fig.layout, "meta", {}) or {}
    return (meta.get("show", {}) if isinstance(meta, dict) else {}) or {}


def _show_layout_shape(fig: go.Figure) -> tuple[int, int]:
    """Return ``(rows, cols)`` for a show figure from metadata or trace count."""
    show_meta = _show_meta(fig)
    rows = int(show_meta.get("rows", 0) or 0)
    cols = int(show_meta.get("cols", 0) or 0)
    if rows > 0 and cols > 0:
        return rows, cols

    n_traces = max(1, len(getattr(fig, "data", []) or []))
    cols = int(math.ceil(math.sqrt(n_traces)))
    rows = int(math.ceil(n_traces / max(1, cols)))
    return rows, cols


def _as_list_of_strings(value: Any) -> list[str]:
    """Normalize a metadata value into a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def _channel_label(channel: str) -> str:
    """Return a friendly display label for a show channel key."""
    normalized = (channel or "").strip().lower()
    labels = {
        "blue": "Blue",
        "green": "Green",
        "green1": "Green",
        "green2": "Green 2",
        "red": "Red",
    }
    return labels.get(normalized, channel.replace("_", " ").title() or "Channel")


def _shorten_label(label: str, width: int) -> str:
    """Shorten a title for static export while preserving useful context."""
    return textwrap.shorten(str(label), width=max(12, width), placeholder="…")


def _trace_z_array(trace: Any) -> np.ndarray | None:
    """Return a finite 2-D array from a Plotly heatmap-like trace."""
    z = getattr(trace, "z", None)
    if z is None:
        return None
    arr = np.asarray(z)
    if arr.ndim != 2:
        return None
    return arr.astype(float, copy=False)


def _trace_bounds(trace: Any, arr: np.ndarray) -> tuple[float, float] | tuple[None, None]:
    """Return display bounds from a trace, falling back to array percentiles."""
    zmin = getattr(trace, "zmin", None)
    zmax = getattr(trace, "zmax", None)
    try:
        if zmin is not None and zmax is not None and float(zmax) > float(zmin):
            return float(zmin), float(zmax)
    except Exception:
        pass

    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None, None
    vmin = float(np.percentile(finite, 0.5))
    vmax = float(np.percentile(finite, 99.5))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        return None, None
    return vmin, vmax


def _static_title_data(fig: go.Figure) -> tuple[bool, list[str], list[str], list[str]]:
    """Return ``(per_file_rows, row_titles, panel_titles, channel_labels)``."""
    show_meta = _show_meta(fig)
    rows, cols = _show_layout_shape(fig)
    per_file_rows = bool(show_meta.get("per_file_rows", False))

    filenames = _as_list_of_strings(show_meta.get("filenames"))
    row_titles = _as_list_of_strings(show_meta.get("row_titles"))
    panel_titles = _as_list_of_strings(show_meta.get("panel_titles"))
    channels = _as_list_of_strings(show_meta.get("channels"))

    if not row_titles:
        row_titles = filenames[:rows]
    if not panel_titles:
        panel_titles = filenames[: max(1, rows * cols)]

    if not channels:
        channels = [f"Channel {i}" for i in range(1, cols + 1)]

    channel_labels = [_channel_label(channel) for channel in channels[:cols]]
    while len(channel_labels) < cols:
        channel_labels.append(f"Channel {len(channel_labels) + 1}")

    return per_file_rows, row_titles, panel_titles, channel_labels


def _style_static_axis(ax: Any) -> None:
    """Apply static show-export styling to an axis."""
    ax.set_facecolor("#2a2a2a")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#555555")
        spine.set_linewidth(0.8)


def _save_static_matplotlib(fig: go.Figure, final_path: str) -> None:
    """Render show heatmap traces to a labeled static file without Kaleido/Chrome.

    The GUI may call this helper from a background worker after the show window
    has closed.  On macOS, importing :mod:`matplotlib.pyplot` from that worker can
    select the native ``macosx`` backend and crash the process because AppKit
    windows must be created on the main thread.  Use Matplotlib's explicit Agg
    canvas instead, which is non-interactive and safe for background exports.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    rows, cols = _show_layout_shape(fig)
    per_file_rows, row_titles, panel_titles, channel_labels = _static_title_data(fig)

    width_px = int(getattr(fig.layout, "width", None) or 1200)
    height_px = int(getattr(fig.layout, "height", None) or max(350, rows * 300))

    figsize = (max(7.5, width_px / 120.0), max(4.5, height_px / 120.0))
    mpl_fig = Figure(figsize=figsize, facecolor="#1a1a1a")
    FigureCanvasAgg(mpl_fig)
    axes = np.asarray(mpl_fig.subplots(rows, cols, squeeze=False), dtype=object)

    # The bottom/right margins are intentionally small because axes have no ticks.
    # Extra top/left room is reserved for filename/channel labels.
    if per_file_rows:
        mpl_fig.subplots_adjust(
            left=0.035,
            right=0.985,
            top=0.86,
            bottom=0.035,
            wspace=0.035,
            hspace=0.36 if rows > 1 else 0.20,
        )
    else:
        mpl_fig.subplots_adjust(
            left=0.025,
            right=0.985,
            top=0.90,
            bottom=0.035,
            wspace=0.045,
            hspace=0.30 if rows > 1 else 0.16,
        )

    try:
        for ax in axes.flat:
            _style_static_axis(ax)

        for idx, trace in enumerate(fig.data):
            if idx >= rows * cols:
                break
            ax = axes.flat[idx]
            arr = _trace_z_array(trace)
            if arr is None:
                ax.set_visible(False)
                continue

            vmin, vmax = _trace_bounds(trace, arr)
            ax.imshow(arr, cmap="gray", origin="upper", vmin=vmin, vmax=vmax, aspect="equal")
            _style_static_axis(ax)

            if per_file_rows:
                # Per-file row labels and per-channel column labels are added
                # after all axes are populated so they can be positioned in
                # figure coordinates without overlapping each other.
                pass
            else:
                panel_label = panel_titles[idx] if idx < len(panel_titles) else f"File {idx + 1}"
                title_parts = [_shorten_label(panel_label, 48)]
                if channel_labels:
                    title_parts.append(channel_labels[0])
                ax.set_title(
                    " — ".join(title_parts),
                    fontsize=10.5,
                    color="#9ef8fd",
                    pad=7,
                    fontweight="bold",
                )

        for idx in range(len(fig.data), rows * cols):
            axes.flat[idx].set_visible(False)

        if per_file_rows:
            visible_top_axes = [axes[0, col_idx] for col_idx in range(cols) if axes[0, col_idx].get_visible()]
            if visible_top_axes:
                top_row_y1 = max(ax.get_position().y1 for ax in visible_top_axes)
                channel_y = min(0.985, top_row_y1 + 0.040)
                first_row_label_y = min(channel_y - 0.026, top_row_y1 + 0.008)
            else:
                top_row_y1 = 0.0
                channel_y = 0.97
                first_row_label_y = 0.944

            for col_idx in range(cols):
                ax0 = axes[0, col_idx]
                if not ax0.get_visible():
                    continue
                bbox = ax0.get_position()
                label = channel_labels[col_idx] if col_idx < len(channel_labels) else f"Channel {col_idx + 1}"
                mpl_fig.text(
                    0.5 * (bbox.x0 + bbox.x1),
                    channel_y,
                    label,
                    ha="center",
                    va="bottom",
                    fontsize=11.5,
                    color="#f0f0f0",
                    fontweight="bold",
                )

            for row_idx in range(rows):
                ax_left = axes[row_idx, 0]
                if not ax_left.get_visible():
                    continue
                bbox = ax_left.get_position()
                row_label = row_titles[row_idx] if row_idx < len(row_titles) else f"File {row_idx + 1}"
                label_y = first_row_label_y if row_idx == 0 else bbox.y1 + 0.004
                mpl_fig.text(
                    bbox.x0,
                    label_y,
                    _shorten_label(row_label, 82),
                    ha="left",
                    va="bottom",
                    fontsize=10.5,
                    color="#9ef8fd",
                    bbox={
                        "boxstyle": "round,pad=0.25",
                        "facecolor": "#1a1a1a",
                        "edgecolor": "#9ef8fd",
                        "linewidth": 0.8,
                    },
                )

        mpl_fig.savefig(final_path, facecolor=mpl_fig.get_facecolor(), bbox_inches="tight", pad_inches=0.08)
    finally:
        mpl_fig.clear()


def save_figure_plotly(fig: go.Figure, save_path: str) -> str:
    """
    Export a Plotly show figure, avoiding overwrites.

    If ``save_path`` has no extension, ``.pdf`` is appended. Static extensions
    ``.pdf``, ``.png``, ``.jpg``, ``.jpeg``, and ``.svg`` are written with a
    Matplotlib renderer that does not require Kaleido or Chrome. ``.html`` and
    ``.htm`` are written as self-contained interactive Plotly files.

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
        If export fails or the chosen output extension is unsupported.
    """
    final_path = _avoid_overwrite(_resolve_show_export_path(save_path))
    suffix = Path(final_path).suffix.lower()

    try:
        if suffix in _HTML_EXPORT_EXTENSIONS:
            fig.write_html(final_path, include_plotlyjs=True, full_html=True)
        else:
            _save_static_matplotlib(fig, final_path)
    except Exception as e:
        raise RuntimeError(
            "Failed to export the show figure. Try saving as .html to preserve the "
            "interactive Plotly figure, or check that the selected output path is writable."
        ) from e

    return final_path
