"""
Entry point for launching the GONet Dashboard.

This module imports the :dashdoc:`Dash <>` `app` instance and provides a top-level `run` function
that starts the dashboard server.

"""

from GONet_Wizard.GONet_dashboard.src.app import app

def run():
    """Start the GONet Dashboard server using :dashdoc:`Dash <>`.

    This function launches the :dashdoc:`Dash <>` app with debugging enabled.
    Typically exposed via the `GONet_dashboard` top-level interface.
    """
    app.run_server(debug=True)

