# GONet_Wizard/commands/show.py

"""
GONet File Visualization Command
================================

This module implements the ``show`` CLI command, which visualizes one or more
GONet image files using Plotly in a multi-panel grid. Panels may represent
different input files, different Bayer color channels, or both, depending on
CLI flags.

The plotting backend uses :class:`plotly.graph_objects.Heatmap` within a
:func:`plotly.subplots.make_subplots` layout to provide reliable rendering in
grid layouts. Axes are configured to lock pixel aspect ratio and synchronize
zoom/pan across all panels.

The command is declared via :data:`COMMAND` and dispatched through
:func:`cli_handler`, which returns a standalone HTML document string suitable
for centralized UI preview. Optional PDF export is supported via Plotly static
image export (Kaleido).

Constants
---------
:class:`COMMAND`
    :class:`~GONet_Wizard.commands.specs.CommandSpec` defining the ``show`` command.

Functions
---------
:func:`auto_vmin_vmax`
    Compute percentile-based display bounds for image intensity.
:func:`build_show_figure`
    Build the Plotly figure for the requested files and channels.
:func:`save_figure_plotly`
    Save a Plotly figure to PDF while avoiding overwriting existing files.
:func:`cli_handler`
    CLI entry point for ``show`` that returns a previewable HTML document.

"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Optional, Sequence, Union

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.commands.cli_core import ExpandFilenames, CommandSpec, filter_by_ext


COMMAND = CommandSpec(
    name="show",
    help="Plot the content of one or more GONet files.",
    args=[
        {
            "flags": ["filenames"],
            "nargs": "+",
            "action": ExpandFilenames,
            "help": (
                "GONet file(s) to plot [.jpg, .tiff]. "
                "`*` wildcards and comma-separated lists are supported."
            ),
        },
        {
            "flags": ["--save"],
            "help": "Save output as a PDF.",
        },
        {
            "flags": ["--blue"],
            "action": "store_true",
            "default": False,
            "help": "Plot only the blue channel.",
        },
        {
            "flags": ["--green"],
            "action": "store_true",
            "default": False,
            "help": "Plot only the green channel.",
        },
        {
            "flags": ["--red"],
            "action": "store_true",
            "default": False,
            "help": "Plot only the red channel.",
        },
    ],
)


def auto_vmin_vmax(
    data: np.ndarray,
    lower_percentile: float = 0.5,
    upper_percentile: float = 99.5,
) -> tuple[float, float]:
    """
    Compute intensity bounds for image display using percentiles.

    Parameters
    ----------
    data : :class:`numpy.ndarray`
        Image array to analyze. Non-finite values are ignored.
    lower_percentile : :class:`float`, optional
        Lower percentile bound used to compute ``vmin``. Defaults to ``0.5``.
    upper_percentile : :class:`float`, optional
        Upper percentile bound used to compute ``vmax``. Defaults to ``99.5``.

    Returns
    -------
    :class:`tuple` of :class:`float`
        ``(vmin, vmax)`` bounds suitable for Plotly heatmap scaling.

    Raises
    ------
    ValueError
        If ``lower_percentile`` or ``upper_percentile`` is outside ``[0, 100]``.
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


def _grid_shape(n: int) -> tuple[int, int]:
    """
    Choose a compact ``(rows, cols)`` grid for ``n`` panels.

    Parameters
    ----------
    n : :class:`int`
        Number of panels.

    Returns
    -------
    :class:`tuple` of :class:`int`
        Grid shape ``(rows, cols)``.

    Raises
    ------
    ValueError
        If ``n`` is less than ``1``.
    """
    if n <= 0:
        raise ValueError("n must be >= 1")
    rows = int(math.sqrt(n))
    cols = int(math.ceil(n / rows))
    return rows, cols


def build_show_figure(
    files: Sequence[Union[str, Path]],
    *,
    blue: bool = False,
    green: bool = False,
    red: bool = False,
    lower_percentile: float = 0.5,
    upper_percentile: float = 99.5,
) -> go.Figure:
    """
    Build a Plotly figure showing one or more GONet files and selected channels.

    Files are expanded into one panel per requested channel. If no channel flags
    are provided, all channels in :data:`GONet_Wizard.GONet_utils.GONetFile.CHANNELS`
    are shown for each file.

    Parameters
    ----------
    files : :class:`~collections.abc.Sequence` of :class:`str` or :class:`pathlib.Path`
        Input files to visualize.
    blue : :class:`bool`, optional
        If ``True``, include the blue channel. Defaults to ``False``.
    green : :class:`bool`, optional
        If ``True``, include the green channel. Defaults to ``False``.
    red : :class:`bool`, optional
        If ``True``, include the red channel. Defaults to ``False``.
    lower_percentile : :class:`float`, optional
        Lower percentile bound for display scaling. Defaults to ``0.5``.
    upper_percentile : :class:`float`, optional
        Upper percentile bound for display scaling. Defaults to ``99.5``.

    Returns
    -------
    :class:`plotly.graph_objects.Figure`
        Plotly figure with one heatmap panel per (file, channel) pair.

    Raises
    ------
    ValueError
        If no panels can be constructed (no files or no channels selected).
    """
    requested = {
        "blue": blue,
        "green": green,
        "red": red,
    }

    # If no channel flags set, show all
    if not any(requested.values()):
        channels = list(GONetFile.CHANNELS)
    else:
        channels = [c for c in GONetFile.CHANNELS if requested.get(c, False)]

    panels: list[tuple[Path, str]] = []
    for f in files:
        p = Path(f)
        for c in channels:
            panels.append((p, c))

    if not panels:
        raise ValueError("No panels to plot (no files or channels selected).")

    rows, cols = _grid_shape(len(panels))

    subplot_titles: list[str] = []
    panel_data: list[np.ndarray] = []
    panel_vmin_vmax: list[tuple[float, float]] = []

    for fpath, c in panels:
        try:
            gof = GONetFile.from_file(str(fpath))
            data = np.asarray(gof.get_channel(c))
        except Exception as e:
            subplot_titles.append(f"{fpath.name} — {c}<br>⚠️ {e}")
            data = np.zeros((10, 10), dtype=np.float32)
            vmin, vmax = 0.0, 1.0
            panel_data.append(data)
            panel_vmin_vmax.append((vmin, vmax))
            continue

        camera = (gof.meta or {}).get("hostname", "")
        date = (gof.meta or {}).get("DateTime", "")

        vmin, vmax = auto_vmin_vmax(
            data,
            lower_percentile=lower_percentile,
            upper_percentile=upper_percentile,
        )

        subplot_titles.append(f"{camera} — {c}<br>{date}")
        panel_data.append(data.astype(np.float32, copy=False))
        panel_vmin_vmax.append((vmin, vmax))

    fig = make_subplots(rows=rows, cols=cols, subplot_titles=subplot_titles)

    for i, (data, (vmin, vmax)) in enumerate(zip(panel_data, panel_vmin_vmax)):
        r = (i // cols) + 1
        c = (i % cols) + 1

        fig.add_trace(
            go.Heatmap(
                z=data,
                colorscale="Gray",
                zmin=vmin,
                zmax=vmax,
                showscale=False,
                hovertemplate="x=%{x}<br>y=%{y}<br>value=%{z}<extra></extra>",
            ),
            row=r,
            col=c,
        )

        fig.update_xaxes(
            showticklabels=False,
            ticks="",
            showgrid=False,
            zeroline=False,
            row=r,
            col=c,
        )
        fig.update_yaxes(
            showticklabels=False,
            ticks="",
            showgrid=False,
            zeroline=False,
            autorange="reversed",
            row=r,
            col=c,
        )

    # --- Lock pixel aspect ratio and sync zoom/pan across panels ---
    n = len(panels)
    for idx in range(1, n + 1):
        xa = f"xaxis{'' if idx == 1 else idx}"
        ya = f"yaxis{'' if idx == 1 else idx}"

        # Sync ranges across all panels
        fig.layout[xa].update(matches="x")
        fig.layout[ya].update(matches="y")

        # Lock aspect ratio: y anchored to its matching x
        xref = f"x{'' if idx == 1 else idx}"
        fig.layout[ya].update(scaleanchor=xref, scaleratio=1)

        # Prevent stretching to fill domain
        fig.layout[xa].update(constrain="domain")
        fig.layout[ya].update(constrain="domain")

    fig.update_layout(
        margin=dict(l=20, r=20, t=60, b=20),
        template="plotly_dark",
        height=max(600, 280 * rows),
        autosize=True,
    )

    return fig


def save_figure_plotly(fig: go.Figure, save_path: str) -> str:
    """
    Save a Plotly figure to PDF, avoiding overwrites.

    Parameters
    ----------
    fig : :class:`plotly.graph_objects.Figure`
        Figure to export.
    save_path : :class:`str`
        Output file path. If it does not end with ``.pdf``, the extension is
        appended. If the path already exists, an index suffix is added.

    Returns
    -------
    :class:`str`
        The final path written to disk.

    Raises
    ------
    RuntimeError
        If Plotly static export fails (commonly due to a missing Kaleido
        installation).
    """
    if not save_path.lower().endswith(".pdf"):
        save_path += ".pdf"

    base, ext = os.path.splitext(save_path)
    counter = 1
    final_path = save_path

    while os.path.exists(final_path):
        final_path = f"{base}_{counter}{ext}"
        counter += 1

    try:
        fig.write_image(final_path)  # requires kaleido
    except Exception as e:
        raise RuntimeError(
            "Failed to write PDF. Plotly static export requires 'kaleido'. "
            "Try: pip install -U kaleido"
        ) from e

    return final_path


def cli_handler(args: argparse.Namespace) -> Optional[str]:
    """
    CLI handler for the ``show`` command.

    This handler filters the provided inputs to supported file types, builds the
    Plotly figure, optionally exports it to PDF, and returns a standalone HTML
    document string for centralized UI preview.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments. Expected to provide ``filenames`` and
        channel selection flags (``blue``, ``green``, ``red``), and optionally
        ``save``.

    Returns
    -------
    :class:`str` or None
        Standalone HTML document string for UI preview. Returns ``None`` only if
        an unrecoverable error prevents figure construction.

    Raises
    ------
    :class:`.ExtensionFilterError`
        If none of the provided paths match the supported extensions.
    RuntimeError
        If ``--save`` is requested and PDF export fails.
    """
    files = filter_by_ext(args.filenames, [".jpg", ".tiff"])

    fig = build_show_figure(
        files,
        blue=args.blue,
        green=args.green,
        red=args.red,
    )

    if args.save:
        out = save_figure_plotly(fig, args.save)
        print(f"✅ Figure saved to {out}")

    return fig.to_html(
        full_html=True,
        include_plotlyjs="inline",
        config={"displaylogo": False, "responsive": True},
    )
