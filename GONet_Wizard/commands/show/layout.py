# GONet_Wizard/commands/show/layout.py

"""
Show Layout Utilities
=====================

This module defines layout policies for the ``show`` command's Plotly figures.

It centralizes three kinds of behavior:

- **Grid geometry**: choose a compact ``(rows, cols)`` arrangement for the
  single-channel case.
- **Axis constraints**: enforce square pixels and deterministic zoom-linking
  behavior across subplot layouts.
- **Decorations**: draw per-file row frames (multi-channel case) and per-panel
  filename "pills" (single-channel grid case). All decoration placement is
  converted from pixel offsets into Plotly "paper" coordinates to keep the
  appearance stable as figure size changes.

Constants
---------
ACCENT
    Accent color used for outlines and highlighted text.
ACCENT_SOFT
    Soft accent color used for subtle backgrounds.
BG_PAGE
    Page background color.
BG_PANEL
    Panel background color (reserved for future use).
BG_CARD
    Card/plot background color.
FG
    Foreground text color.
BORDER
    Border color used for pill outlines.

Functions
---------
grid_shape_smart
    Choose a compact ``(rows, cols)`` grid for ``n`` panels.

apply_aspect_ratio_lock
    Enforce square pixels in every subplot using Plotly axis constraints.

build_zoom_payloads
    Build relayout payloads for zoom-linking modes (all, file, none).

apply_default_zoom_matches
    Apply an initial zoom-linking mode directly to the figure layout.

add_panel_title_pills
    Add per-panel filename pills in the single-channel grid layout.

add_file_row_frames
    Draw a rectangular frame and header band for each file row in the
    multi-channel layout.
"""

from __future__ import annotations

import math

import plotly.graph_objects as go

ACCENT = "rgb(158,248,253)"
ACCENT_SOFT = "rgba(158,248,253,0.12)"
BG_PAGE = "#1a1a1a"
BG_PANEL = "#1e1e1e"
BG_CARD = "#2a2a2a"
FG = "#f0f0f0"
BORDER = "rgba(158,248,253,0.45)"


def grid_shape_smart(n: int) -> tuple[int, int]:
    """
    Choose a compact ``(rows, cols)`` grid for ``n`` panels.

    Parameters
    ----------
    n : :class:`int`
        Number of panels.

    Returns
    -------
    :class:`tuple` [:class:`int`, :class:`int`]
        ``(rows, cols)`` for a compact grid.

    Raises
    ------
    :class:`ValueError`
        If ``n`` is less than 1.
    """
    if n <= 0:
        raise ValueError("n must be >= 1")
    rows = int(math.sqrt(n))
    cols = int(math.ceil(n / rows))
    return rows, cols


def _axis_name(axis: str, idx: int) -> str:
    """
    Build a Plotly axis layout key (e.g. ``'xaxis'``, ``'xaxis2'``).

    Parameters
    ----------
    axis : :class:`str`
        Base axis name (``'xaxis'`` or ``'yaxis'``).
    idx : :class:`int`
        1-based subplot index.

    Returns
    -------
    :class:`str`
        Plotly axis layout key.
    """
    return axis if idx == 1 else f"{axis}{idx}"


def _axis_ref(axis: str, idx: int) -> str:
    """
    Build a Plotly axis reference (e.g. ``'x'``, ``'x2'``) for matching.

    Parameters
    ----------
    axis : :class:`str`
        Base axis reference (``'x'`` or ``'y'``).
    idx : :class:`int`
        1-based subplot index.

    Returns
    -------
    :class:`str`
        Plotly axis reference string.
    """
    return axis if idx == 1 else f"{axis}{idx}"


def apply_aspect_ratio_lock(fig: go.Figure, *, rows: int, cols: int) -> None:
    """
    Lock pixel aspect ratio for all subplots (square pixels).

    This ensures that image pixels remain square when zooming or resizing, by
    tying each y-axis scale to its corresponding x-axis.

    Parameters
    ----------
    fig : :class:`plotly.graph_objects.Figure`
        Target figure.
    rows : :class:`int`
        Number of subplot rows.
    cols : :class:`int`
        Number of subplot columns.

    Returns
    -------
    :class:`None`

    """
    n = rows * cols
    for i in range(1, n + 1):
        xa = _axis_name("xaxis", i)
        ya = _axis_name("yaxis", i)
        xref = _axis_ref("x", i)

        fig.layout[ya].update(scaleanchor=xref, scaleratio=1)
        fig.layout[xa].update(constrain="domain")
        fig.layout[ya].update(constrain="domain")


def _build_matches_payload(*, rows: int, cols: int, mode: str, per_file_rows: bool) -> dict:
    """
    Build a relayout payload that sets axis ``matches`` properties.

    Parameters
    ----------
    rows : :class:`int`
        Number of subplot rows.
    cols : :class:`int`
        Number of subplot columns.
    mode : :class:`str`
        Zoom-linking mode:

        - ``'all'``: all subplots share one zoom state
        - ``'file'``: subplots match *within each row* (only meaningful when
          ``per_file_rows`` is ``True``)
        - ``'none'``: no matching; each subplot zooms independently
    per_file_rows : :class:`bool`
        Whether the layout is "one row per file".

    Returns
    -------
    :class:`dict`
        Relayout payload mapping keys like ``"xaxis2.matches"`` to values.

    """
    n = rows * cols
    mode = (mode or "all").strip().lower()
    if mode not in {"all", "file", "none"}:
        mode = "all"

    d: dict = {}

    if mode == "none":
        for i in range(1, n + 1):
            d[f"{_axis_name('xaxis', i)}.matches"] = None
            d[f"{_axis_name('yaxis', i)}.matches"] = None
        return d

    if mode == "all":
        for i in range(1, n + 1):
            d[f"{_axis_name('xaxis', i)}.matches"] = "x"
            d[f"{_axis_name('yaxis', i)}.matches"] = "y"
        return d

    # mode == "file"
    if not per_file_rows:
        for i in range(1, n + 1):
            d[f"{_axis_name('xaxis', i)}.matches"] = None
            d[f"{_axis_name('yaxis', i)}.matches"] = None
        return d

    for r in range(1, rows + 1):
        base_idx = (r - 1) * cols + 1
        bx = _axis_ref("x", base_idx)
        by = _axis_ref("y", base_idx)
        for c in range(1, cols + 1):
            idx = (r - 1) * cols + c
            d[f"{_axis_name('xaxis', idx)}.matches"] = bx
            d[f"{_axis_name('yaxis', idx)}.matches"] = by

    return d


def build_zoom_payloads(*, rows: int, cols: int, per_file_rows: bool) -> dict[str, dict]:
    """
    Build relayout payloads for the zoom-linking modes used by the HTML controls.

    Parameters
    ----------
    rows : :class:`int`
        Number of subplot rows.
    cols : :class:`int`
        Number of subplot columns.
    per_file_rows : :class:`bool`
        Whether the layout is "one row per file".

    Returns
    -------
    :class:`dict` [:class:`str`, :class:`dict`]
        Mapping of ``'all'``, ``'file'``, and ``'none'`` to Plotly relayout
        payload dictionaries.

    """
    return {
        "all": _build_matches_payload(rows=rows, cols=cols, mode="all", per_file_rows=per_file_rows),
        "file": _build_matches_payload(rows=rows, cols=cols, mode="file", per_file_rows=per_file_rows),
        "none": _build_matches_payload(rows=rows, cols=cols, mode="none", per_file_rows=per_file_rows),
    }


def apply_default_zoom_matches(
    fig: go.Figure,
    *,
    rows: int,
    cols: int,
    mode: str,
    per_file_rows: bool,
) -> None:
    """
    Apply an initial zoom-linking mode directly to the figure layout.

    This is used to set the *starting* state of axis matching, before any HTML
    controls call :meth:`plotly.graph_objects.Figure.relayout`.

    Parameters
    ----------
    fig : :class:`plotly.graph_objects.Figure`
        Target figure.
    rows : :class:`int`
        Number of subplot rows.
    cols : :class:`int`
        Number of subplot columns.
    mode : :class:`str`
        Initial mode (``'all'``, ``'file'``, or ``'none'``).
    per_file_rows : :class:`bool`
        Whether the layout is "one row per file".

    Returns
    -------
    :class:`None`

    """
    payload = _build_matches_payload(rows=rows, cols=cols, mode=mode, per_file_rows=per_file_rows)
    for k, v in payload.items():
        axis_name, prop = k.split(".")
        fig.layout[axis_name][prop] = v


def add_panel_title_pills(
    fig: go.Figure,
    *,
    rows: int,
    cols: int,
    titles: list[str],
    title_max_chars: int = 42,
    title_pad_x_px: int = 12,
    title_pad_y_px: int = -10,
) -> None:
    """
    Add per-panel title pills for the single-channel grid layout.

    Each pill is an annotation placed *inside* the corresponding subplot, near
    the top-left corner. Offsets are specified in pixels and converted into
    paper coordinates using the figure's plot area, so placement remains stable
    under deterministic resizing.

    Parameters
    ----------
    fig : :class:`plotly.graph_objects.Figure`
        Target figure.
    rows : :class:`int`
        Number of subplot rows.
    cols : :class:`int`
        Number of subplot columns.
    titles : :class:`list` [:class:`str`]
        Title strings in subplot insertion order (the same order used when
        traces are added).
    title_max_chars : :class:`int`, optional
        Maximum displayed length; longer titles are truncated with an ellipsis.
    title_pad_x_px : :class:`int`, optional
        X offset from the subplot's left edge, in pixels.
    title_pad_y_px : :class:`int`, optional
        Y offset relative to the subplot's top edge, in pixels. Negative values
        move the pill downward into the panel.

    Returns
    -------
    :class:`None`

    """
    n = rows * cols
    if n <= 0:
        return

    height_px = int(getattr(fig.layout, "height", 800) or 800)
    width_px = int(getattr(fig.layout, "width", 1200) or 1200)

    margin = getattr(fig.layout, "margin", None)
    mt = int(getattr(margin, "t", 0) or 0)
    mb = int(getattr(margin, "b", 0) or 0)
    ml = int(getattr(margin, "l", 0) or 0)
    mr = int(getattr(margin, "r", 0) or 0)

    plot_h_px = max(1, height_px - mt - mb)
    plot_w_px = max(1, width_px - ml - mr)

    title_pad_x = title_pad_x_px / plot_w_px
    title_pad_y = title_pad_y_px / plot_h_px

    for i in range(1, n + 1):
        idx = i - 1
        if idx >= len(titles):
            break

        xa = _axis_name("xaxis", i)
        ya = _axis_name("yaxis", i)

        x0, _x1 = map(float, fig.layout[xa].domain)
        _y0, y1 = map(float, fig.layout[ya].domain)

        title = titles[idx]
        if len(title) > title_max_chars:
            title = title[: title_max_chars - 1] + "…"

        fig.add_annotation(
            x=x0 + title_pad_x,
            y=y1 - title_pad_y,
            xref="paper",
            yref="paper",
            text=title,
            showarrow=False,
            xanchor="left",
            yanchor="top",
            bgcolor=BG_PAGE,
            bordercolor=BORDER,
            borderwidth=1,
            borderpad=3,
            font=dict(size=12, color=ACCENT),
        )


def add_file_row_frames(
    fig: go.Figure,
    *,
    rows: int,
    cols: int,
    row_titles: list[str],
    pad_x_px: int = 12,
    pad_y_px: int = 10,
    header_px: int = 56,
    label_y_px: int = 22,
    title_max_chars: int = 70,
) -> None:
    """
    Draw a frame around each file-row and reserve a constant-height header band.

    This is used for the multi-channel layout (one row per file). Two things
    happen per row:

    1. **Reserve header height in pixels** by shrinking each subplot's y-domain
       upward, leaving a consistent band for column labels.
    2. **Create breathing room at the left/right edges** by shrinking each
       subplot's x-domain inward by ``pad_x_px`` (converted to paper fraction).
       This avoids image traces visually "touching" the row border.

    Parameters
    ----------
    fig : :class:`plotly.graph_objects.Figure`
        Target figure.
    rows : :class:`int`
        Number of subplot rows (files).
    cols : :class:`int`
        Number of subplot columns (channels).
    row_titles : :class:`list` [:class:`str`]
        One title per row. Values are truncated to ``title_max_chars``.
    pad_x_px : :class:`int`, optional
        Horizontal padding in pixels used to shrink subplot x-domains.
    pad_y_px : :class:`int`, optional
        Extra padding below the row frame, in pixels.
    header_px : :class:`int`, optional
        Header band height reserved inside each row, in pixels.
    label_y_px : :class:`int`, optional
        Vertical placement for the column labels within the header band, in pixels.
    title_max_chars : :class:`int`, optional
        Maximum displayed title length; longer titles are truncated with an ellipsis.

    Returns
    -------
    :class:`None`

    """
    if rows <= 0 or cols <= 0:
        return

    labels = ["Blue", "Green", "Red"][:cols]

    height_px = int(getattr(fig.layout, "height", 800) or 800)
    width_px = int(getattr(fig.layout, "width", 1200) or 1200)

    margin = getattr(fig.layout, "margin", None)
    mt = int(getattr(margin, "t", 0) or 0)
    mb = int(getattr(margin, "b", 0) or 0)
    ml = int(getattr(margin, "l", 0) or 0)
    mr = int(getattr(margin, "r", 0) or 0)

    plot_h_px = max(1, height_px - mt - mb)
    plot_w_px = max(1, width_px - ml - mr)

    header_h_nominal = header_px / plot_h_px
    pad_y = pad_y_px / plot_h_px
    pad_x_frac = pad_x_px / plot_w_px
    label_offset = label_y_px / plot_h_px * 2

    # Title pill padding (px -> paper coords).
    title_pad_x_px = 12
    title_pad_y_px = 15
    title_pad_x = title_pad_x_px / plot_w_px
    title_pad_y = title_pad_y_px / plot_h_px

    for r in range(1, rows + 1):
        idx_first = (r - 1) * cols + 1
        idx_last = (r - 1) * cols + cols

        ya_first = _axis_name("yaxis", idx_first)
        xa_first = _axis_name("xaxis", idx_first)
        xa_last = _axis_name("xaxis", idx_last)

        # Row bounds from first/last subplot domains (before mutation).
        x0 = float(fig.layout[xa_first].domain[0])
        x1 = float(fig.layout[xa_last].domain[1])
        y0 = float(fig.layout[ya_first].domain[0])
        y1 = float(fig.layout[ya_first].domain[1])

        row_h = max(1e-9, y1 - y0)
        header_h = min(header_h_nominal, 0.45 * row_h)
        panel_y1 = y1 - header_h

        # Reserve header: shrink y-domains for each subplot in the row.
        for c in range(1, cols + 1):
            idx = (r - 1) * cols + c
            ya = _axis_name("yaxis", idx)
            oldy = fig.layout[ya].domain
            fig.layout[ya].domain = [float(oldy[0]), float(panel_y1)]

        # Shrink x-domains for breathing room.
        for c in range(1, cols + 1):
            idx = (r - 1) * cols + c
            xa = _axis_name("xaxis", idx)
            oldx0, oldx1 = map(float, fig.layout[xa].domain)

            newx0 = oldx0 + pad_x_frac
            newx1 = oldx1 - pad_x_frac
            if newx1 <= newx0 + 1e-6:
                continue

            fig.layout[xa].domain = [newx0, newx1]

        # Compute column centers after x-domain shrink.
        col_centers: list[float] = []
        for c in range(1, cols + 1):
            idx = (r - 1) * cols + c
            xa = _axis_name("xaxis", idx)
            dx0 = float(fig.layout[xa].domain[0])
            dx1 = float(fig.layout[xa].domain[1])
            col_centers.append(0.5 * (dx0 + dx1))

        # Frame box is tied to original row bounds, not the shrunken domains.
        fx0 = max(0.0, x0)
        fx1 = min(1.0, x1)
        fy0 = max(0.0, y0 - pad_y)
        fy1 = y1

        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=fx0,
            x1=fx1,
            y0=fy0,
            y1=fy1,
            line=dict(width=2, color=ACCENT),
            fillcolor="rgba(0,0,0,0)",
            layer="below",
        )

        # Title pill anchored above the row frame.
        title = row_titles[r - 1] if r - 1 < len(row_titles) else f"File {r}"
        if len(title) > title_max_chars:
            title = title[: title_max_chars - 1] + "…"

        fig.add_annotation(
            x=fx0 + title_pad_x,
            y=fy1 + title_pad_y,
            xref="paper",
            yref="paper",
            text=title,
            showarrow=False,
            xanchor="left",
            yanchor="top",
            bgcolor=BG_PAGE,
            bordercolor=BG_PAGE,
            borderwidth=1,
            borderpad=4,
            font=dict(size=16, color=ACCENT),
        )

        # Column labels inside header band.
        y_label = fy1 - label_offset
        for c, label in enumerate(labels):
            fig.add_annotation(
                x=col_centers[c],
                y=y_label,
                xref="paper",
                yref="paper",
                text=f"<b>{label}</b>",
                showarrow=False,
                xanchor="center",
                yanchor="middle",
                font=dict(size=16, color=FG),
            )
