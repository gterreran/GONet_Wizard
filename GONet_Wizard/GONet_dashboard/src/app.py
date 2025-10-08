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

from GONet_Wizard import settings
from GONet_Wizard.GONet_dashboard.src.server import app
import threading, webview, logging
from GONet_Wizard.gui_launcher.api import WebviewAPI

def run_dashboard():
    """
    Configure and run the Dash application server.

    This function:

    - Toggles logging verbosity based on the debug setting.
    - Imports and applies the application layout from :mod:`layout`.
    - Registers all Dash callbacks from :mod:`callbacks`.
    - Redefines the HTML template to include custom CSS and JavaScript assets.
    - Starts the Dash server on ``localhost:8050``.
        
    """

    if not settings.DASHBOARD_DEBUG:
        # Suppress Flask/Werkzeug/Dash startup logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger("dash.dash").setLevel(logging.ERROR)
        import flask.cli
        flask.cli.show_server_banner = lambda *args, **kwargs: None

    from GONet_Wizard.GONet_dashboard.src.layout import layout
    app.layout = layout

    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
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

    from GONet_Wizard.GONet_dashboard.src import callbacks

    app.run_server(port=8050, debug=settings.DASHBOARD_DEBUG, use_reloader=False)


def launch_dashboard():
    """
    Public entry point to launch the GONet Dashboard in a PyWebview window.

    This function:

    - Configures the GONet Dashboard app by performing environment validation,
    - Spawns a daemon thread running :func:`run_app` to start the Dash server.
    - Waits briefly to ensure the server is ready.
    - Creates a PyWebview window pointing to the Dash app URL and passes an
      instance of :class:`ExitAPI` as the JavaScript API for window control.
    - Starts the PyWebview event loop.

    Returns
    -------
    None

    """

    config = settings.DashboardConfig()

    # Optionally store config globally if needed in callbacks
    import GONet_Wizard.GONet_dashboard.src.env as env
    env.DASHBOARD_DATA_PATH = config.dashboard_data_path
    env.GONET_IMAGES_PATH = config.gonet_images_path

    # Start Dash server in a background thread
    dash_thread = threading.Thread(target=run_dashboard)
    dash_thread.daemon = True
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