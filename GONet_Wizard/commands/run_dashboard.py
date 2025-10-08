"""
Entry point for launching the GONet Dashboard.

This module imports the `Dash <https://dash.plotly.com/>`_ `app` instance and provides a top-level
function to start the server. 

**Functions**

- :func:`run` : Launch the GONet Dashboard server using `Dash <https://dash.plotly.com/>`_.

"""

from GONet_Wizard.GONet_dashboard.src.app import launch_dashboard

def run():
    """
    Launch the GONet Dashboard in a standalone PyWebview window.

    Returns
    -------
    None
    """

    launch_dashboard()
