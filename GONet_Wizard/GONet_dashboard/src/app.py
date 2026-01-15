# GONet_Wizard/GONet_dashboard/src/app.py

"""
GONet Dashboard Application Entrypoint
======================================

This module defines the public entry point used to launch the GONet interactive
dashboard within the unified GONet Wizard UI runtime.

Unlike earlier standalone implementations, the dashboard is now launched through
the centralized Dash orchestration layer provided by
:mod:`GONet_Wizard.ui.dash_runner`. This enables:

- Reuse of a single Dash server per (app_key, port)
- Consistent startup semantics across CLI and GUI invocations
- Integration with the unified Flask + pywebview UI runtime
- Clean separation between *what* the dashboard does and *how* it is launched

The core responsibility of this module is to assemble a
:class:`~GONet_Wizard.ui.dash_runner.DashLaunchSpec` describing how to configure,
lay out, and run the dashboard, and to delegate execution to
:func:`~GONet_Wizard.ui.dash_runner.ensure_dash_running`.

Functions
---------
:func:`ensure_dashboard_running`
    Public entry point used by CLI and GUI commands to launch (or reuse) the
    dashboard Dash server.
"""

from __future__ import annotations

from typing import List

from GONet_Wizard.GONet_dashboard.src.server import app
from GONet_Wizard.GONet_dashboard.src.hood.loaders import load_data
from GONet_Wizard.ui.dash_runner import DashLaunchSpec, ensure_dash_running


def _configure_dashboard(
    input_files: List[str],
    show_images_preview: bool,
    images_path: List[str],
) -> None:
    """
    Populate the Dash server configuration with dashboard data and metadata.

    This function loads the input data and stores all required objects in
    ``app.server.config`` so they are available to layout construction and
    callbacks without recomputation.

    Parameters
    ----------
    input_files : :class:`list` of :class:`str`
        Paths to input JSON/CSV files to load into the dashboard.
    show_images_preview : :class:`bool`
        Whether image previews should be enabled in the UI.
    images_path : :class:`list` of :class:`str`
        Paths to directories containing GONet images.

    Returns
    -------
    None
    """
    data, base_columns, channel_columns = load_data(input_files)

    app.server.config.update(
        data=data,
        base_columns=base_columns,
        channel_columns=channel_columns,
        show_images_preview=show_images_preview,
        images_path=images_path,
    )

    # Precompute dropdown options shared across multiple callbacks
    all_columns = [{"label": l, "value": l} for l in base_columns + channel_columns]
    app.server.config["all_columns"] = all_columns


def _layout(_app):
    """
    Construct and return the Dash layout for the dashboard.

    The layout is built dynamically using values stored in
    ``app.server.config`` during configuration.

    Parameters
    ----------
    _app : :class:`dash.Dash`
        The Dash application instance.

    Returns
    -------
    object
        A Dash-compatible layout component tree.
    """
    from GONet_Wizard.GONet_dashboard.src.layout import layout

    cfg = _app.server.config
    return layout(cfg["show_images_preview"], cfg["all_columns"])


def _register_callbacks() -> None:
    """
    Register all Dash callbacks for the dashboard.

    Callbacks are imported for their side effects and are expected to register
    themselves with the Dash app at import time.

    Returns
    -------
    None
    """
    from GONet_Wizard.GONet_dashboard.src import callbacks  # noqa: F401


def _index_string() -> str:
    """
    Return a custom Dash ``index_string`` for the dashboard.

    This override injects custom branding, favicon, and shared CSS used by the
    unified UI runtime.

    Returns
    -------
    :class:`str`
        A complete Dash index template.
    """
    return """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            <link rel="icon" href="/img/logo/favicon.ico" type="image/x-icon">
            {%css%}
            <link rel="stylesheet" href="/assets/css/style.css">
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """


def ensure_dashboard_running(
    input_files: List[str],
    show_images_preview: bool,
    images_path: List[str],
    debug: bool,
    port: int = 8050,
) -> str:
    """
    Ensure the GONet dashboard Dash server is running and return its URL.

    This function is safe to call repeatedly. If a dashboard instance is already
    running for the given ``port``, it is reused. Otherwise, a new Dash server
    is started in a background thread using the centralized Dash runner.

    Parameters
    ----------
    input_files : :class:`list` of :class:`str`
        Paths to input JSON/CSV files to load into the dashboard.
    show_images_preview : :class:`bool`
        Whether image previews should be enabled in the UI.
    images_path : :class:`list` of :class:`str`
        Paths to directories containing GONet images.
    debug : :class:`bool`
        Whether to run Dash in debug mode.
    port : :class:`int`, optional
        Localhost port to bind the Dash server to.

    Returns
    -------
    :class:`str`
        The local dashboard URL (e.g. ``"http://127.0.0.1:8050"``).
    """
    spec = DashLaunchSpec(
        app=app,
        app_key="gonet-dashboard",
        configure=lambda _app: _configure_dashboard(
            input_files,
            show_images_preview,
            images_path,
        ),
        layout=_layout,
        register_callbacks=_register_callbacks,
        index_string=_index_string,
    )

    return ensure_dash_running(spec, debug=debug, port=port)
