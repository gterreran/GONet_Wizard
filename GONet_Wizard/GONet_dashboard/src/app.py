"""
GONet Wizard Dashboard Application Entry Point.

This script initializes the `Dash <https://dash.plotly.com/>`_ application.
First it verifies that critical environment variables used by the dashboard
are set before launching. Specifically, it initializes the
:class:`GONet_Wizard.settings.DashboardConfig` to trigger
validation for ``GONET_ROOT`` and optionally ``GONET_ROOT_IMG``.
Then it sets the app's layout, and registers
all callback functions that define the app's interactivity.

The layout and callbacks are modularized for clarity and maintainability.

This script should be used as the WSGI entry point when deploying the app
(e.g. Gunicorn).
"""

# Import the initialized Dash app instance
from GONet_Wizard.GONet_dashboard.src.server import app
from GONet_Wizard.settings import DashboardConfig

config = DashboardConfig()

# Import the main layout and assign it to the app
from GONet_Wizard.GONet_dashboard.src.layout import layout
app.layout = layout

# Register all callback functions
from GONet_Wizard.GONet_dashboard.src import callbacks

