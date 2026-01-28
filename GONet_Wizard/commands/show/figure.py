# GONet_Wizard/commands/show/figure.py

"""
Show Figure Builder
===================

This module constructs the Plotly :class:`~plotly.graph_objects.Figure` used by the
``show`` command.

The design goal is *deterministic sizing* in a PyWebView context, where responsive
HTML can otherwise cause row spacing and layout to "breathe" depending on the number
of subplots. To keep the visual rhythm stable:

- Figure width is derived from the PyWebView window width.
- Figure height is derived from either:
  - one "row per file" sizing when plotting multiple channels, or
  - a compact grid sizing when plotting a single channel across multiple files.
- Pixel spacing (row gaps, header bands, title offsets) is converted to paper
  coordinates (fractions) using the figure's effective plot area.

This module also loads GONet files, prepares per-channel intensity bounds, and
emits either:

- per-file row frames (multi-channel case) via
  :func:`~GONet_Wizard.commands.show.layout.add_file_row_frames`, or
- per-panel filename "pills" (single-channel grid case) via
  :func:`~GONet_Wizard.commands.show.layout.add_panel_title_pills`.

Classes
-------
_LoadedFile
    Internal container for loaded file data and derived display bounds.

Functions
---------
auto_vmin_vmax
    Compute percentile-based display bounds for image-like arrays.

build_show_figure
    Build the :class:`~plotly.graph_objects.Figure` for the ``show`` command.

_load_files
    Load one or more files into a normalized internal representation.

_representative_hw
    Pick a representative image height/width for sizing heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from GONet_Wizard.GONet_utils import GONetFile

from .layout import (
    add_file_row_frames,
    add_panel_title_pills,
    apply_aspect_ratio_lock,
    apply_default_zoom_matches,
    grid_shape_smart,
    BG_CARD,
    BG_PAGE,
    FG,
)


@dataclass
class _LoadedFile:
    """
    Loaded GONet file data for figure construction.

    Attributes
    ----------
    path : :class:`pathlib.Path`
        Path of the input file.
    meta : :class:`dict`
        Parsed metadata dictionary (may be empty if loading failed).
    data : :class:`dict`
        Mapping of channel name -> image array (:class:`numpy.ndarray`).
    bounds : :class:`dict`
        Mapping of channel name -> ``(vmin, vmax)`` bounds (:class:`tuple` of
        :class:`float`).
    error : :class:`str` or :class:`None`
        Error message if loading failed; ``None`` on success.
    """

    path: Path
    meta: dict
    data: dict
    bounds: dict
    error: Optional[str] = None


def auto_vmin_vmax(
    data: np.ndarray,
    lower_percentile: float = 0.5,
    upper_percentile: float = 99.5,
) -> tuple[float, float]:
    """
    Compute robust display bounds for an image using percentiles.

    Parameters
    ----------
    data : :class:`numpy.ndarray`
        Image-like array.
    lower_percentile : :class:`float`, optional
        Lower percentile used for ``vmin``. Defaults to ``0.5``.
    upper_percentile : :class:`float`, optional
        Upper percentile used for ``vmax``. Defaults to ``99.5``.

    Returns
    -------
    :class:`tuple` [:class:`float`, :class:`float`]
        ``(vmin, vmax)`` suitable for Plotly ``zmin``/``zmax``.

    Notes
    -----
    If percentile computation results in non-finite or degenerate bounds, this
    falls back to ``min``/``max`` of finite values and enforces ``vmax > vmin``.
    """
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0

    vmin = float(np.percentile(finite, lower_percentile))
    vmax = float(np.percentile(finite, upper_percentile))

    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin = float(np.min(finite))
        vmax = float(np.max(finite))
        if vmax <= vmin:
            vmax = vmin + 1.0

    return vmin, vmax


def _load_files(
    files: Sequence[Union[str, Path]],
    *,
    channels: Sequence[str],
    lower_percentile: float = 0.5,
    upper_percentile: float = 99.5,
) -> list[_LoadedFile]:
    """
    Load input files and extract channel arrays and display bounds.

    Parameters
    ----------
    files : :class:`collections.abc.Sequence` [:class:`str` or :class:`pathlib.Path`]
        Paths to input GONet files.
    channels : :class:`collections.abc.Sequence` [:class:`str`]
        Channel names to load from each file.
    lower_percentile : :class:`float`, optional
        Percentile for ``vmin`` passed to :func:`auto_vmin_vmax`.
    upper_percentile : :class:`float`, optional
        Percentile for ``vmax`` passed to :func:`auto_vmin_vmax`.

    Returns
    -------
    :class:`list` [:class:`~GONet_Wizard.commands.show.figure._LoadedFile`]
        A list of loaded file containers. On failure, a placeholder array is used
        and the error message is recorded.

    """
    loaded: list[_LoadedFile] = []

    for f in files:
        path = Path(f)
        meta: dict = {}
        data: dict = {}
        bounds: dict = {}

        try:
            gof = GONetFile.from_file(str(path))
            meta = gof.meta or {}

            for ch in channels:
                arr = np.asarray(gof.get_channel(ch)).astype(np.float32, copy=False)
                data[ch] = arr
                bounds[ch] = auto_vmin_vmax(
                    arr,
                    lower_percentile=lower_percentile,
                    upper_percentile=upper_percentile,
                )

            loaded.append(_LoadedFile(path=path, meta=meta, data=data, bounds=bounds, error=None))

        except Exception as e:
            # Provide a deterministic placeholder so downstream layout remains valid.
            for ch in channels:
                arr = np.zeros((10, 10), dtype=np.float32)
                data[ch] = arr
                bounds[ch] = (0.0, 1.0)

            loaded.append(_LoadedFile(path=path, meta=meta, data=data, bounds=bounds, error=str(e)))

    return loaded


def _representative_hw(loaded: list[_LoadedFile], channels: Sequence[str]) -> tuple[int, int]:
    """
    Choose a representative (height, width) from the loaded data.

    Parameters
    ----------
    loaded : :class:`list` [:class:`~GONet_Wizard.commands.show.figure._LoadedFile`]
        Loaded file containers.
    channels : :class:`collections.abc.Sequence` [:class:`str`]
        Channels available for lookup.

    Returns
    -------
    :class:`tuple` [:class:`int`, :class:`int`]
        Representative ``(height, width)`` in pixels.

    Raises
    ------
    :class:`IndexError`
        If ``loaded`` is empty.
    :class:`KeyError`
        If a requested channel key is missing in the selected reference file.
    """
    channels_list = list(channels)

    for lf in loaded:
        for ch in channels_list:
            arr = lf.data.get(ch)
            if arr is None:
                continue
            h, w = arr.shape[:2]
            if h >= 100 and w >= 100:
                return int(h), int(w)

    lf0 = loaded[0]
    arr0 = lf0.data[channels_list[0]]
    h, w = arr0.shape[:2]
    return int(h), int(w)


def build_show_figure(
    files: Sequence[Union[str, Path]],
    channels: Sequence[str],
    *,
    lower_percentile: float = 0.5,
    upper_percentile: float = 99.5,
    window_width_px: int = 1250,
    window_height_px: int = 800,
    width_frac: float = 0.95,
    row_height_frac: float = 0.50,
) -> go.Figure:
    """
    Build the Plotly figure for the ``show`` command.

    Parameters
    ----------
    files : :class:`collections.abc.Sequence` [:class:`str` or :class:`pathlib.Path`]
        Input file paths.
    channels : :class:`collections.abc.Sequence` [:class:`str`]
        Channel names to plot. If length is ``1``, a compact grid is used. If
        length is greater than ``1``, the figure uses one row per file and one
        column per channel.
    lower_percentile : :class:`float`, optional
        Lower percentile for display bounds.
    upper_percentile : :class:`float`, optional
        Upper percentile for display bounds.
    window_width_px : :class:`int`, optional
        Target UI window width in pixels (used for deterministic sizing).
    window_height_px : :class:`int`, optional
        Target UI window height in pixels (used for deterministic sizing).
    width_frac : :class:`float`, optional
        Fraction of the window width used for the figure width.
    row_height_frac : :class:`float`, optional
        Fraction of the window height used for each per-file row in the
        multi-channel layout.

    Returns
    -------
    :class:`plotly.graph_objects.Figure`
        Fully constructed and styled figure.

    Raises
    ------
    :class:`ValueError`
        If ``channels`` is empty.
    """
    channels = list(channels)
    if not channels:
        raise ValueError("No channels selected.")

    loaded = _load_files(
        files,
        channels=channels,
        lower_percentile=lower_percentile,
        upper_percentile=upper_percentile,
    )

    # Determine subplot geometry.
    if len(channels) == 1:
        rows, cols = grid_shape_smart(len(loaded))
        per_file_rows = False
    else:
        rows = len(loaded)
        cols = len(channels)
        per_file_rows = True

    # Titles for the single-channel grid case (one pill per panel).
    panel_titles: list[str] = []
    if not per_file_rows:
        for lf in loaded:
            panel_titles.append(f"{lf.path.name} — ⚠️ {lf.error}" if lf.error else lf.path.name)

    # Margin policy: buttons are outside Plotly; keep plot margins compact.
    margin = dict(l=20, r=20, t=20, b=20)

    # Pixel-tuned spacing knobs.
    row_gap_px = 36
    header_px = 56

    width_px = int(max(600, window_width_px * float(width_frac)))
    base_row_height_px = int(max(200, window_height_px * float(row_height_frac)))

    img_h, img_w = _representative_hw(loaded, channels)

    if per_file_rows:
        plot_px = rows * base_row_height_px + max(0, rows - 1) * row_gap_px
        height_px = margin["t"] + margin["b"] + plot_px
    else:
        panel_w_px = int(max(160, (width_px - margin["l"] - margin["r"]) / max(1, cols)))
        panel_h_px = int(max(120, panel_w_px * (img_h / max(1, img_w))))
        plot_px = rows * panel_h_px + max(0, rows - 1) * 24
        height_px = margin["t"] + margin["b"] + plot_px

    plot_h_px = max(1, height_px - margin["t"] - margin["b"])
    vertical_spacing = (row_gap_px / plot_h_px) if (rows > 1) else 0.06

    fig = make_subplots(rows=rows, cols=cols, vertical_spacing=vertical_spacing)

    # Add image traces.
    if len(channels) == 1:
        ch0 = channels[0]
        for i, lf in enumerate(loaded):
            r = (i // cols) + 1
            c = (i % cols) + 1

            z = lf.data[ch0]
            vmin, vmax = lf.bounds[ch0]

            fig.add_trace(
                go.Heatmap(
                    z=z,
                    colorscale="Gray",
                    zmin=vmin,
                    zmax=vmax,
                    showscale=False,
                    hovertemplate="x=%{x}<br>y=%{y}<br>value=%{z}<extra></extra>",
                ),
                row=r,
                col=c,
            )

            h, w = z.shape
            fig.update_xaxes(range=[0, w], row=r, col=c, showticklabels=False, ticks="", showgrid=False, zeroline=False)
            fig.update_yaxes(range=[h, 0], row=r, col=c, showticklabels=False, ticks="", showgrid=False, zeroline=False)

    else:
        for r, lf in enumerate(loaded, start=1):
            for c, ch in enumerate(channels, start=1):
                z = lf.data[ch]
                vmin, vmax = lf.bounds[ch]

                fig.add_trace(
                    go.Heatmap(
                        z=z,
                        colorscale="Gray",
                        zmin=vmin,
                        zmax=vmax,
                        showscale=False,
                        hovertemplate="x=%{x}<br>y=%{y}<br>value=%{z}<extra></extra>",
                    ),
                    row=r,
                    col=c,
                )

                h, w = z.shape
                fig.update_xaxes(range=[0, w], row=r, col=c, showticklabels=False, ticks="", showgrid=False, zeroline=False)
                fig.update_yaxes(range=[h, 0], row=r, col=c, showticklabels=False, ticks="", showgrid=False, zeroline=False)

    # Per-file row titles for the multi-channel case.
    row_titles: list[str] = []
    if per_file_rows:
        for lf in loaded:
            camera = (lf.meta or {}).get("hostname", "")
            date = (lf.meta or {}).get("DateTime", "")
            fname = lf.path.name
            row_titles.append(f"{fname} — ⚠️ {lf.error}" if lf.error else f"{camera} — {fname} — {date}")

    # Cosmetics + sizing.
    fig.update_layout(
        template=None,
        paper_bgcolor=BG_PAGE,
        plot_bgcolor=BG_CARD,
        font=dict(family="Fira Sans, Segoe UI, sans-serif", color=FG, size=14),
        margin=margin,
        width=width_px,
        height=height_px,
        autosize=False,
    )

    # Default zoom matching (initial).
    apply_default_zoom_matches(fig, rows=rows, cols=cols, mode="all", per_file_rows=per_file_rows)

    # Titles/frames.
    if not per_file_rows:
        add_panel_title_pills(fig, rows=rows, cols=cols, titles=panel_titles)
    else:
        add_file_row_frames(
            fig,
            rows=rows,
            cols=cols,
            row_titles=row_titles,
            header_px=header_px,
            pad_y_px=10,
            label_y_px=22,
        )

    apply_aspect_ratio_lock(fig, rows=rows, cols=cols)

    # Expose layout info for the external HTML controls.
    fig.update_layout(
        meta={
            "show": {
                "rows": rows,
                "cols": cols,
                "per_file_rows": per_file_rows,
            }
        }
    )

    return fig
