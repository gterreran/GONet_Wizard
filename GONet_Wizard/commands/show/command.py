# GONet_Wizard/commands/show/command.py

"""
Show Command
============

This module defines the :class:`~GONet_Wizard.commands.cli_core.CommandSpec` for the
``show`` command and implements its CLI handler.

The ``show`` command renders one or more GONet files as a Plotly figure and returns
an HTML document (as a string) intended to be displayed by the GUI layer (e.g. a
PyWebView window).

Unlike earlier versions, we do **not** rely on Plotly ``updatemenus`` for zoom-link
controls. Instead, we generate a small, custom HTML "chrome" (buttons + optional
channel label) around the Plotly figure. This keeps the controls visually consistent
with the rest of the GONet Wizard UI (via ``style.css``) and gives deterministic
control over layout, spacing, and styling that is hard to achieve with Plotly's
built-in menu widgets.

The returned HTML embeds the Plotly figure and a tiny script that maps button clicks
to :meth:`plotly.graph_objects.Figure.relayout` via ``Plotly.relayout(...)``.

Constants
---------
COMMAND
    The :class:`~GONet_Wizard.commands.cli_core.CommandSpec` for the ``show`` command.

Functions
---------
cli_handler
    CLI entry-point for ``show``. Builds the figure and returns the HTML document.

_int_or_default
    Helper to parse an integer CLI value with a safe fallback.

_resolve_channels
    Resolves which channels should be displayed based on CLI flags.
"""

from __future__ import annotations

import argparse
import json
from typing import Optional

import plotly.io as pio

from GONet_Wizard.commands.cli_core import CommandSpec, ExpandFilenames, filter_by_ext
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.settings import STATIC

from .figure import build_show_figure
from .io import save_figure_plotly
from .layout import build_zoom_payloads


_channel_flags = [
    {
        "flags": [f"--{c}"],
        "action": "store_true",
        "default": False,
        "help": f"Plot only the {c} channel.",
    }
    for c in GONetFile.CHANNELS
]

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
            "flags": ["--calibrator"],
            "help": "Optional .npz file containing a fitted PolarHarmonicCalibrator.",
        }
    ]
    + _channel_flags,
)


def _int_or_default(value: object, default: int) -> int:
    """
    Convert an arbitrary value to a positive integer, or fall back to a default.

    Parameters
    ----------
    value : :class:`object`
        Value to interpret as an integer. Typically comes from an
        :class:`argparse.Namespace`.
    default : :class:`int`
        Value to return if parsing fails or the parsed integer is not positive.

    Returns
    -------
    :class:`int`
        A positive integer.

    Notes
    -----
    This intentionally catches all exceptions because CLI values may be missing,
    ``None``, or non-numeric depending on how the caller constructs ``args``.
    """
    try:
        v = int(value)  # type: ignore[arg-type]
        return v if v > 0 else default
    except Exception:
        return default


def _resolve_channels(*, blue: bool, green: bool, red: bool) -> list[str]:
    """
    Determine which channels should be plotted given CLI channel flags.

    Parameters
    ----------
    blue : :class:`bool`
        Whether the ``--blue`` channel flag was provided.
    green : :class:`bool`
        Whether the ``--green`` channel flag was provided.
    red : :class:`bool`
        Whether the ``--red`` channel flag was provided.

    Returns
    -------
    :class:`list` [:class:`str`]
        List of channel names to plot. If no flags are provided, all channels are
        returned in the canonical order from :class:`~GONet_Wizard.GONet_utils.GONetFile`.

    Raises
    ------
    :class:`ValueError`
        If the resolved channel list is empty (should only occur if the underlying
        channel list is empty or inconsistent).
    """
    requested = {"blue": blue, "green": green, "red": red}
    if not any(requested.values()):
        channels = list(GONetFile.CHANNELS)
    else:
        channels = [c for c in GONetFile.CHANNELS if requested.get(c, False)]

    if not channels:
        raise ValueError("No channels selected.")
    return channels


def cli_handler(args: argparse.Namespace) -> Optional[str]:
    """
    Build and render the ``show`` output as a standalone HTML document.

    The handler:

    1. Resolves input files and channel selection from CLI arguments.
    2. Builds a Plotly figure using :func:`~GONet_Wizard.commands.show.figure.build_show_figure`.
    3. Optionally saves the figure (e.g. PDF) via :func:`~GONet_Wizard.commands.show.io.save_figure_plotly`.
    4. Computes "zoom linking" payloads and emits custom HTML buttons that call
       ``Plotly.relayout(graphDiv, payload)``.
    5. Returns the HTML string to the UI layer (PyWebView / GUI launcher) for display.

    We generate the HTML here (instead of relying on Plotly ``updatemenus``) because
    it provides deterministic control over the UI "chrome":

    - Layout is stable across different grid shapes (single-channel grids vs
      per-file rows) and across different WebView implementations.
    - The UI is decoupled from Plotly's menu rendering quirks and limitations.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed CLI arguments as created by :data:`COMMAND`.

    Returns
    -------
    :class:`str` or :class:`None`
        A complete HTML document as a string. If your surrounding CLI framework
        supports "no UI output" paths, this may return ``None`` (currently unused).

    Raises
    ------
    :class:`FileNotFoundError`
        If the required CSS file (``STATIC/css/style.css``) is missing.
    :class:`ValueError`
        If no channels are selected.
    """
    files = filter_by_ext(args.filenames, [".jpg", ".tiff"])

    blue = bool(getattr(args, "blue", False))
    green = bool(getattr(args, "green", False))
    red = bool(getattr(args, "red", False))
    channels = _resolve_channels(blue=blue, green=green, red=red)

    # Defaults consistent with your WindowSpec (ui_bridge)
    window_w = _int_or_default(getattr(args, "window_width_px", None), 1250)
    window_h = _int_or_default(getattr(args, "window_height_px", None), 800)

    if getattr(args, "calibrator", None):
        from GONet_Wizard.GONet_utils.src.calibrators.distortion import PolarHarmonicCalibrator

        calibrator = PolarHarmonicCalibrator.from_fit_npz(args.calibrator)
    else:
        calibrator = None

    fig = build_show_figure(
        files,
        channels=channels,
        window_width_px=window_w,
        window_height_px=window_h,
        width_frac=0.90,
        row_height_frac=0.40,
        calibrator=calibrator
    )

    if getattr(args, "save", None):
        out = save_figure_plotly(fig, str(args.save))
        print(f"✅ Figure saved to {out}")

    # Geometry needed for zoom-link payloads (stored in fig.layout.meta by figure.py)
    meta = getattr(fig.layout, "meta", {}) or {}
    show_meta = (meta.get("show", {}) if isinstance(meta, dict) else {}) or {}
    rows = int(show_meta.get("rows", 1) or 1)
    cols = int(show_meta.get("cols", 1) or 1)
    per_file_rows = bool(show_meta.get("per_file_rows", False))
    payloads = build_zoom_payloads(rows=rows, cols=cols, per_file_rows=per_file_rows)

    # Explicit graph height to prevent vertical inflation with responsive Plotly.
    height_px = _int_or_default(getattr(fig.layout, "height", None), window_h)

    div_id = "gonet-show-plot"
    plot_html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs="inline",
        div_id=div_id,
        default_width="100%",
        default_height=f"{height_px}px",
        config={
            "displaylogo": False,
            "responsive": True,
            "displayModeBar": False,
        },
    )

    css_path = STATIC / "css" / "style.css"
    if not css_path.exists():
        raise FileNotFoundError(f"Required CSS file not found: {css_path}")
    css_text = css_path.read_text(encoding="utf-8")

    payloads_json = json.dumps(payloads)

    channel_html = ""
    if len(channels) == 1:
        single_channel_label = channels[0].capitalize()
        channel_html = f'<span class="gw-channel-label">Channel: {single_channel_label}</span>'

    # Custom HTML wrapper + JS to wire buttons -> Plotly.relayout
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
{css_text}
  </style>
</head>
<body>
  <div class="gw-controls-row">
    <div class="gw-controls" role="group" aria-label="Zoom controls">
      <span class="label">Zoom mode</span>
      <button type="button" class="zoom-btn active" data-mode="all">All</button>
      <button type="button" class="zoom-btn" data-mode="file">Same file</button>
      <button type="button" class="zoom-btn" data-mode="none">Independent</button>
    </div>
    {channel_html}
  </div>

  <div class="gw-plot-wrap">
    {plot_html}
  </div>

  <script>
  (function() {{
    const divId = {json.dumps(div_id)};
    const payloads = {payloads_json};

    function getGraphDiv() {{
      return document.getElementById(divId);
    }}

    function setActive(mode) {{
      document.querySelectorAll('.zoom-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.mode === mode);
      }});
    }}

    function applyMode(mode) {{
      const gd = getGraphDiv();
      if (!gd || !window.Plotly) return;

      const payload = payloads[mode] || payloads['all'];
      window.Plotly.relayout(gd, payload);
      setActive(mode);
    }}

    document.querySelectorAll('.zoom-btn').forEach(btn => {{
      btn.addEventListener('click', () => applyMode(btn.dataset.mode));
    }});

    requestAnimationFrame(() => applyMode('all'));
  }})();
  </script>
</body>
</html>
"""
    return html
