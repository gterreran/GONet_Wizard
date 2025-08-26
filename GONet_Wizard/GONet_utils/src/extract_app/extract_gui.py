"""
Entry point for launching the GONet extraction GUI as a standalone desktop
window using `PyWebview <https://pywebview.flowrl.com/>`_ .

This module wraps the Dash-based extraction app in a lightweight desktop
environment. It suppresses standard Flask, Werkzeug, and Dash startup banners
to keep the launch sequence clean, and exposes a JavaScript API to allow the
Dash frontend to trigger native window actions (such as closing the app).

**Classes**

- :class:`GONetAPI`:
    A JavaScript API exposed to the PyWebview window

**Functions**

- :func:`run_app`:
    Initializes the Dash layout, registers callbacks, suppresses startup
    banners/logs, and starts the server on a background thread.
- :func:`launch_extraction_gui`:
    Public entry point that spawns the Dash server thread, waits for it to
    start, then creates and runs a PyWebview window displaying the GUI.

"""

from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
import threading, webview, logging, json


def run_app():
    """
    Configure the Dash application, suppress startup banners, and run the server.

    This function:

    - Raises the log level of the ``werkzeug`` and ``dash.dash`` loggers to
      suppress request logs and Dash's startup banner.
    - Monkey-patches :func:`flask.cli.show_server_banner` to suppress Flask's
      CLI banner lines.
    - Imports and applies the application layout from
      :mod:`extract_layout`.
    - Registers all Dash callbacks from :mod:`extract_callbacks`.
    - Starts the Dash server on ``localhost:8050`` with reloading disabled.

    Notes
    -----
    This function is intended to be run in a background thread to allow the
    main thread to remain responsive for PyWebview's event loop.
    """
    # Suppress Flask/Werkzeug/Dash startup logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger("dash.dash").setLevel(logging.ERROR)
    import flask.cli
    flask.cli.show_server_banner = lambda *args, **kwargs: None

    # Set up the app layout and callbacks
    from GONet_Wizard.GONet_utils.src.extract_app.extract_layout import layout
    app.layout = layout

    from GONet_Wizard.GONet_utils.src.extract_app import extract_callbacks

    # Start the Dash server (blocking call until thread exit)
    app.run_server(port=8050, debug=False, use_reloader=False)


class GONetAPI:
    """
    JavaScript API for PyWebview interactions including window control and JSON downloads.

    This object is exposed to JavaScript as `window.pywebview.api`, allowing your
    Dash frontend to call methods like `download_json()` and `close_window()`.

    Methods
    -------
    download_json(data: dict):
        Prompts the user with a file dialog and saves `data` as a formatted JSON file.

    close_window():
        Gracefully closes the PyWebview window after a short delay.
    """

    def download_json(self, data: dict) -> None:
        """Save the given data dictionary as a JSON file using a save dialog."""
        window = webview.windows[0]

        if not hasattr(window, 'create_file_dialog'):
            print("File dialog not supported in current backend.")
            return

        path = window.create_file_dialog(
            webview.SAVE_DIALOG,
            file_types=('JSON files (*.json)', 'All files (*.*)')
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
    

    def close_window(self) -> None:
        """Schedule the destruction of the current PyWebview window."""
        threading.Timer(0.1, lambda: webview.windows[0].destroy()).start()


def launch_extraction_gui(data_files):
    """
    Launch the extraction GUI in a standalone PyWebview window.

    This function:

    - Stores ``data_files`` in the Flask server config so the Dash app can
      access them when rendering the layout.
    - Spawns a daemon thread running :func:`run_app` to start the Dash server.
    - Waits briefly to ensure the server is ready.
    - Creates a PyWebview window pointing to the Dash app URL and passes an
      instance of :class:`ExitAPI` as the JavaScript API for window control.
    - Starts the PyWebview event loop, which blocks until the window is closed.
    - After the GUI closes, checks whether ``extraction_params`` were stored
      in the server config during the session. If present, returns them so
      the caller can proceed with the extraction outside of the GUI.

    Parameters
    ----------
    data_files : :class:`list` of :class:`str`
        List of data file paths to be made available to the GUI.

    Returns
    -------
    :class:`dict` or :data:`None`
        The extraction parameters stored in
        ``app.server.config["extraction_params"]`` during the GUI session,
        or ``None`` if no parameters were set by the user.
    """
    # Make data_files available to the Dash server
    app.server.config["data_files"] = data_files

    # Start Dash server in a background thread
    dash_thread = threading.Thread(target=run_app)
    dash_thread.daemon = True
    dash_thread.start()

    # Give Dash a moment to initialize
    import time
    time.sleep(1)

    # Create and run the PyWebview window
    webview.create_window(
        "My Dash App",
        "http://127.0.0.1:8050",
        width=1250,
        height=700,
        js_api=GONetAPI()
    )
    webview.start()

    if "extraction_params" in app.server.config:
        # Return the extraction parameters if they were set in the GUI
        # This allows the caller to access them after the GUI is closed
        return app.server.config["extraction_params"]
    else:
        # If no parameters were set, return None
        return None
