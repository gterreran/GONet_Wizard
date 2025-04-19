"""
GONet Wizard Dashboard Application Entry Point.

This script initializes the `Dash <https://dash.plotly.com/>`_ application, sets its layout,
and registers all callback functions that define the app's interactivity.

The layout and callbacks are modularized for clarity and maintainability.

This script should be used as the WSGI entry point when deploying the app
(e.g. Gunicorn).
"""

# Import the initialized Dash app instance
from GONet_Wizard.GONet_dashboard.src.server import app

# Import the main layout and assign it to the app
from GONet_Wizard.GONet_dashboard.src.layout import layout
app.layout = layout

# Register all callback functions
from GONet_Wizard.GONet_dashboard.src import callbacks

