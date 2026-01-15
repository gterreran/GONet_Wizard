# GONet_Wizard/ui/server.py

"""
Unified Local UI Server for Desktop Runtime
===========================================

This module hosts the unified Flask server used by the GONet Wizard desktop UI.
The server provides a single local HTTP surface for:

- the GUI launcher pages (main menu and command forms),
- preview endpoints for command output (e.g. ``/view/<channel>``), and
- future UI endpoints shared across windows.

The server is started on demand via :func:`ensure_server_running` and runs in a
single daemon thread. This allows CLI commands and UI workflows to publish and
render previews without requiring an external web server setup.

Global State
------------
The server is managed as a process singleton using module-level state:

- ``_app`` holds the :class:`flask.Flask` instance
- ``_server_thread`` holds the background thread running the server
- ``_server_port`` stores the configured port

Functions
---------
:func:`create_app`
    Create and configure the unified Flask application.
:func:`ensure_server_running`
    Start the Flask server thread if needed and return the active port.
:func:`get_app`
    Return the singleton Flask app instance, creating it if needed.
:func:`get_server_port`
    Return the configured server port.

"""

from __future__ import annotations

import threading
import time
from typing import Optional

from flask import Flask

from GONet_Wizard import settings


_server_thread: Optional[threading.Thread] = None
_server_port: int = 5050
_app: Optional[Flask] = None


def create_app() -> Flask:
    """
    Create the unified Flask application for the desktop UI runtime.

    The returned app registers blueprints for the GUI launcher pages and the
    preview subsystem. Template and static folders are configured using package
    settings so the app can be run from different working directories.

    Returns
    -------
    :class:`flask.Flask`
        Configured Flask application instance.

    Raises
    ------
    RuntimeError
        If blueprint registration fails due to import cycles or missing assets.
    """
    app = Flask(
        "GONetWizardUI",
        template_folder=str(settings.ROOT / "gui" / "templates"),
        static_folder=settings.STATIC,
    )

    # Register the launcher routes as a blueprint
    try:
        from GONet_Wizard.gui.web import launcher_bp  # imported here to avoid cycles
        app.register_blueprint(launcher_bp)
    except Exception as e:
        raise RuntimeError("Failed to register launcher blueprint.") from e

    # Register preview endpoints
    try:
        from GONet_Wizard.ui.preview import preview_bp
        app.register_blueprint(preview_bp)
    except Exception as e:
        raise RuntimeError("Failed to register preview blueprint.") from e

    return app


def ensure_server_running(*, port: int = 5050) -> int:
    """
    Ensure the unified Flask server is running and return the port.

    This function is safe to call multiple times. If the server thread is
    already running, the existing port is returned. Otherwise, the server is
    created and started in a single daemon thread.

    Parameters
    ----------
    port : :class:`int`, optional
        Localhost port to bind the server to. Defaults to ``5050``.

    Returns
    -------
    :class:`int`
        The port the server is running on.

    Raises
    ------
    RuntimeError
        If the server cannot be started.
    """
    global _server_thread, _server_port, _app

    if _server_thread is not None and _server_thread.is_alive():
        return _server_port

    _server_port = port
    _app = create_app()

    def _run() -> None:
        # threaded=True allows concurrent requests from multiple windows
        _app.run(
            host="127.0.0.1",
            port=_server_port,
            debug=False,
            threaded=True,
            use_reloader=False,
        )

    try:
        _server_thread = threading.Thread(target=_run, daemon=True)
        _server_thread.start()
    except Exception as e:
        raise RuntimeError("Failed to start unified UI server thread.") from e

    # Give it a moment to bind the port
    time.sleep(0.25)
    return _server_port


def get_app() -> Flask:
    """
    Return the singleton Flask app instance, creating it if needed.

    This helper is primarily intended for tests or advanced embedding scenarios.

    Returns
    -------
    :class:`flask.Flask`
        The process singleton Flask application instance.
    """
    global _app
    if _app is None:
        _app = create_app()
    return _app


def get_server_port() -> int:
    """
    Return the configured server port (whether started or not).

    Returns
    -------
    :class:`int`
        Port currently stored in module state.
    """
    return _server_port
