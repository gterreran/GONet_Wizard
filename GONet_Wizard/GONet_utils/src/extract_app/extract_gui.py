# GONet_Wizard/GONet_utils/src/extract_app/extract_gui.py

"""
GONet Extraction GUI Entrypoint
===============================

This module defines the Dash application entry point for the GONet extraction
GUI. The extraction GUI provides an interactive interface for defining regions
of interest and extracting pixel counts from GONet image files.

As with the main dashboard, this GUI is no longer launched as a standalone Dash
application. Instead, it is integrated into the centralized Dash orchestration
layer provided by :mod:`GONet_Wizard.ui.dash_runner`. This allows the extraction
GUI to be:

- Launched from both CLI and HTML-based GUI contexts
- Reused across multiple invocations without restarting the server
- Embedded consistently within the unified Flask + pywebview UI runtime

This module is responsible only for *describing* how the extraction Dash app
should be configured and launched. All lifecycle management is delegated to
the shared Dash runner.

Functions
---------
:func:`ensure_dashboard_running`
    Public entry point used by CLI and GUI commands to launch (or reuse) the
    extraction GUI Dash server.
"""

from __future__ import annotations

from typing import List

from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
from GONet_Wizard.ui.dash_runner import DashLaunchSpec, ensure_dash_running

def _configure_extract_gui(data_files: List[str]) -> None:
    """
    Populate the Dash server configuration for the extraction GUI.

    The list of data files is stored in ``app.server.config`` so it is accessible
    to layout construction and callback logic without repeated parsing.

    Parameters
    ----------
    data_files : :class:`list` of :class:`str`
        Paths to GONet image files to be used for extraction.

    Returns
    -------
    None
    """
    app.server.config.update(data_files=data_files)


def _layout(_app):
    """
    Return the Dash layout for the extraction GUI.

    The layout is imported lazily to avoid unnecessary imports at module load
    time and to keep initialization lightweight.

    Parameters
    ----------
    _app : :class:`dash.Dash`
        The Dash application instance.

    Returns
    -------
    object
        A Dash-compatible layout component tree.
    """
    from GONet_Wizard.GONet_utils.src.extract_app.extract_layout import layout
    return layout


def _register_callbacks() -> None:
    """
    Register all Dash callbacks for the extraction GUI.

    Callback registration is performed via import side effects. Importing the
    callbacks module is sufficient to attach all required interactions to the
    Dash application.

    Returns
    -------
    None
    """
    from GONet_Wizard.GONet_utils.src.extract_app import extract_callbacks  # noqa: F401


def ensure_extraction_gui_running(
    data_files: List[str],
    debug: bool,
    port: int = 8051,
) -> str:
    """
    Ensure the extraction GUI Dash server is running and return its URL.

    This function is safe to call repeatedly. If a server instance for the
    extraction GUI is already running on the given ``port``, it is reused.
    Otherwise, a new Dash server is started in a background thread using the
    centralized Dash runner.

    Parameters
    ----------
    data_files : :class:`list` of :class:`str`
        Paths to GONet image files to be used for extraction.
    debug : :class:`bool`
        Whether to run Dash in debug mode.
    port : :class:`int`, optional
        Localhost port to bind the Dash server to.

    Returns
    -------
    :class:`str`
        The local URL of the extraction GUI
        (e.g. ``"http://127.0.0.1:8051"``).
    """
    spec = DashLaunchSpec(
        app=app,
        app_key="extract-gui",
        configure=lambda _app: _configure_extract_gui(data_files),
        layout=_layout,
        register_callbacks=_register_callbacks,
    )

    return ensure_dash_running(spec, debug=debug, port=port)
