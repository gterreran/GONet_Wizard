"""
Entry point for launching the GONet Dashboard.

This module imports the `Dash <https://dash.plotly.com/>`_ `app` instance and provides a top-level
function to start the server. It also verifies that critical environment variables
used by the dashboard are set before launching.

Environment
-----------
- ``GONET_ROOT`` : Required path to the dashboard's data directory.
- ``ROOT_EXT`` : Optional path to image resources.

**Functions**

- :func:`run_dashboard` : Start the GONet Dashboard server using `Dash <https://dash.plotly.com/>`_.

"""

from GONet_Wizard.GONet_dashboard.src.app import app
from GONet_Wizard.commands.settings import DashboardConfig


def run_dashboard():
    """
    Start the GONet Dashboard server using `Dash <https://dash.plotly.com/>`_.

    This function launches the dashboard and performs
    a pre-check to ensure that required environment variables are defined.
    Specifically, it initializes the :class:`GONet_Wizard.commands.settings.DashboardConfig` to trigger
    validation for ``GONET_ROOT`` and optionally ``ROOT_EXT``.

    Returns
    -------
    None
    """
    config = DashboardConfig()
    config.dashboard_data_path   # Triggers env check for GONET_ROOT
    config.gonet_images_path     # Triggers optional env check for ROOT_EXT

    app.run_server(debug=True)
