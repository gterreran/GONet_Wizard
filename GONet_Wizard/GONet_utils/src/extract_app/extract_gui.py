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

from typing import Any, List, Optional

from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
from GONet_Wizard.ui.dash_runner import DashLaunchSpec, ensure_dash_running


EXTRACT_GUI_WINDOW_KEY = "extract-gui"
_INTERACTIVE_EXTRACTION_SUBMITTED_KEY = "interactive_extraction_submitted"


def mark_interactive_extraction_submitted() -> None:
    """Mark the active interactive extraction session as intentionally submitted."""
    app.server.config[_INTERACTIVE_EXTRACTION_SUBMITTED_KEY] = True


def _clear_terminal_stream_if_current(terminal_stream: Optional[Any]) -> None:
    """Clear ``terminal_stream`` from app config if it is still active."""
    if terminal_stream is not None and app.server.config.get("terminal_stream") is terminal_stream:
        app.server.config["terminal_stream"] = None


def cancel_interactive_extraction_if_unsubmitted() -> None:
    """Finish the form stream when the extraction window closes without Extract.

    Closing the pywebview window via the title-bar X bypasses Dash callbacks.
    The launcher form is still waiting on its original streaming response, so
    this window-close hook emits the same final status that the explicit Exit
    button would have emitted.  If the user clicked Extract, the worker thread
    owns the stream and this hook deliberately does nothing.
    """
    if app.server.config.get(_INTERACTIVE_EXTRACTION_SUBMITTED_KEY):
        return

    terminal_stream = app.server.config.get("terminal_stream")
    if terminal_stream is not None and not terminal_stream.is_done:
        terminal_stream.finish(
            status="error",
            message="Interactive extraction cancelled before output was written.",
        )
    _clear_terminal_stream_if_current(terminal_stream)


def _configure_extract_gui(
    data_files: List[str],
    channels: Optional[List[str]] = None,
    output: Optional[str] = None,
    output_type: Optional[str] = None,
    terminal_stream: Optional[Any] = None,
) -> None:
    """
    Populate the Dash server configuration for the extraction GUI.

    The list of data files is stored in ``app.server.config`` so it is accessible
    to layout construction and callback logic without repeated parsing.

    Parameters
    ----------
    data_files : :class:`list` of :class:`str`
        Paths to GONet image files to be used for extraction.
    channels : :class:`list` of :class:`str`, optional
        Channels to extract when the user clicks the Extract button.  If not
        provided, all standard GONet channels are extracted.
    output : :class:`str`, optional
        Output path requested by the caller.  If not provided, the extraction
        callback writes the usual ``extraction_<shape>.json`` file.
    output_type : :class:`str`, optional
        Requested output type, either ``"json"`` or ``"csv"``.
    terminal_stream : object, optional
        Stream bridge used by the launcher GUI terminal panel. When present,
        extraction callback output is forwarded to the original command stream.

    Returns
    -------
    None
    """
    app.server.config.update(
        data_files=data_files,
        channels=channels or ["red", "green", "blue"],
        output=output,
        output_type=output_type,
        terminal_stream=terminal_stream,
    )
    app.server.config[_INTERACTIVE_EXTRACTION_SUBMITTED_KEY] = False


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
    channels: Optional[List[str]] = None,
    output: Optional[str] = None,
    output_type: Optional[str] = None,
    terminal_stream: Optional[Any] = None,
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
    channels : :class:`list` of :class:`str`, optional
        Channels to extract when the user clicks the Extract button.  If not
        provided, all standard GONet channels are extracted.
    output : :class:`str`, optional
        Output path requested by the caller.  If not provided, the extraction
        callback writes the usual ``extraction_<shape>.json`` file.
    output_type : :class:`str`, optional
        Requested output type, either ``"json"`` or ``"csv"``.
    terminal_stream : object, optional
        Stream bridge used by the launcher GUI terminal panel. When present,
        extraction callback output is forwarded to the original command stream.

    Returns
    -------
    :class:`str`
        The local URL of the extraction GUI
        (e.g. ``"http://127.0.0.1:8051"``).
    """
    spec = DashLaunchSpec(
        app=app,
        app_key="extract-gui",
        configure=lambda _app: _configure_extract_gui(
            data_files,
            channels=channels,
            output=output,
            output_type=output_type,
            terminal_stream=terminal_stream,
        ),
        layout=_layout,
        register_callbacks=_register_callbacks,
    )

    return ensure_dash_running(spec, debug=debug, port=port)
