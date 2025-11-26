"""
GONet Wizard Dashboard Application Entry Point.

This module initializes the GONet Wizard `Dash <https://dash.plotly.com/>`_ application
and performs environment validation before interactive components are used.

Key responsibilities:

- Loads and validates critical environment variables through :class:`DashboardConfig`
- Assigns data and image paths to the shared `env` module used across the dashboard
- Imports and registers all callback functions to enable interactivity
- Ensures that configuration logic is only executed when explicitly called (e.g., at launch)
- Provides a function to launch the dashboard in a `PyWebview <https://pywebview.flowrl.com/>`_ window

**Functions**

- :func:`run_dashboard`:
    Configures and runs the Dash application server.
- :func:`launch_dashboard`:
    Public entry point to launch the GONet Dashboard in a PyWebview window.

"""

from GONet_Wizard.GONet_dashboard.src.server import app
import threading, webview, logging
from GONet_Wizard.gui_launcher.api import WebviewAPI
from typing import List
from GONet_Wizard.GONet_dashboard.src.hood.loaders import load_data

def run_dashboard(all_columns: List[dict], debug: bool) -> None:
    """
    Configure and run the Dash application server.

    This function:

    - Toggles logging verbosity based on the debug setting.
    - Imports and applies the application layout from :mod:`layout`.
    - Registers all Dash callbacks from :mod:`callbacks`.
    - Redefines the HTML template to include custom CSS and JavaScript assets.
    - Starts the Dash server on ``localhost:8050``.
    
    Parameters
    ----------
    json_files : :class:`list` of :class:`str`
        List of paths to JSON files to load data from.
    show_images_preview : :class:`bool`
        Whether to show image previews in the dashboard.
    images_path : :class:`list` of :class:`str`
        List of paths to directories containing images.
    debug : :class:`bool`
        Whether to run the server in debug mode.

    Returns
    -------
    None

    """

    if not debug:
        # Suppress Flask/Werkzeug/Dash startup logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger("dash.dash").setLevel(logging.ERROR)
        import flask.cli
        flask.cli.show_server_banner = lambda *args, **kwargs: None

    from GONet_Wizard.GONet_dashboard.src.layout import layout
    app.layout = layout(app.server.config["show_images_preview"], all_columns)

    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            <link rel="icon" href="/img/logo/favicon.ico" type="image/x-icon">
            {%css%}
            <link rel="stylesheet" href="/assets/css/style.css">
            <script src="/assets/js/launcher.js"></script>
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
    '''

    from GONet_Wizard.GONet_dashboard.src import callbacks # noqa: F401

    app.run_server(port=8050, debug=debug, use_reloader=False)


def launch_dashboard(input_files: List[str], show_images_preview: bool, images_path: List[str], debug: bool) -> None:
    """
    Public entry point to launch the GONet Dashboard in a PyWebview window.

    This function:

    - Loads data from the specified JSON files
    - Stores loaded data and configuration in the Dash app server config. Note: we
      cannot store parameters needed by the layout because of import order constraints,
      so we pass these via kwargs to :func:`run_dashboard`.
    - Spawns a daemon thread running :func:`run_dashboard` to start the Dash server.
    - Waits briefly to ensure the server is ready.
    - Creates a PyWebview window pointing to the Dash app URL and passes an
      instance of :class:`ExitAPI` as the JavaScript API for window control.
    - Starts the PyWebview event loop.

    Parameters
    ----------
    input_files : :class:`list` of :class:`str`
        List of paths to input files to load data from.
    show_images_preview : :class:`bool`
        Whether to show image previews in the dashboard.
    images_path : :class:`list` of :class:`str`
        List of paths to directories containing images.
    debug : :class:`bool`
        Whether to run the server in debug mode.

    Returns
    -------
    None

    """

    # Load data and store in app config for access in callbacks
    data, base_columns, channel_columns = load_data(input_files)
    app.server.config["data"] = data
    app.server.config["base_columns"] = base_columns
    app.server.config["channel_columns"] = channel_columns
    app.server.config["show_images_preview"] = show_images_preview
    app.server.config["images_path"] = images_path

    all_columns = [{"label": l, "value": l} for l in base_columns + channel_columns]

    # Start Dash server in a background thread
    dash_thread = threading.Thread(
    target=run_dashboard,
    kwargs={
        "all_columns": all_columns,
        "debug": debug
    },
    daemon=True,
)
    dash_thread.start()

    # Give Dash a moment to initialize
    import time
    time.sleep(1)

    # Create and run the PyWebview window
    webview.create_window(
        "GONet Wizard extraction GUI",
        "http://127.0.0.1:8050",
        width=1250,
        height=700,
        js_api=WebviewAPI()
    )
    webview.start()