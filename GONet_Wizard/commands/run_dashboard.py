"""
Entry point for launching the GONet Dashboard.

This module imports the `Dash <https://dash.plotly.com/>`_ `app` instance and provides a top-level
function to start the server. 

**Functions**

- :func:`run_dashboard` : Start the GONet Dashboard server using `Dash <https://dash.plotly.com/>`_.

"""

from GONet_Wizard.GONet_dashboard.src.app import app

def run():
    """
    Start the GONet Dashboard server using `Dash <https://dash.plotly.com/>`_.

    Returns
    -------
    None
    """

    app.run_server(debug=True)
