"""
GONet Wizard Dashboard Application Entry Point.

This script initializes the Dash application, sets its layout,
and registers all callback functions that define the app's interactivity.

The layout and callbacks are modularized for clarity and maintainability.

Modules Imported
----------------
- `server`: Provides the `app` object, which is a Dash instance wrapped around a Flask server.
- `layout`: Contains the full layout definition (Divs, Graphs, Controls).
- `callbacks`: Registers all Dash callbacks for user interaction.

Notes
-----
This script should be used as the WSGI entry point when deploying the app
(e.g., with Gunicorn or `python app.py` for development).
"""

# Import the initialized Dash app instance
from GONet_Wizard.GONet_dashboard.src.server import app

# Import the main layout and assign it to the app
from GONet_Wizard.GONet_dashboard.src.layout import layout
app.layout = layout

# Register all callback functions
from GONet_Wizard.GONet_dashboard.src import callbacks

