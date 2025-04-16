"""
The `GONet_dashboard` module contains the logic and components for running 
and managing the GONet Wizard dashboard, built with :dashdoc:`Plotly Dash <>`. The module
includes the app layout, callbacks, and server configuration.

This subpackage provides the user interface for exploring GONet camera data
interactively. It exposes a single top-level function:

Functions
---------
:func:`GONet_Wizard.GONet_dashboard.run` : Starts the dashboard server.

Example
-------
To launch the dashboard from your code:

>>> from GONet_Wizard import GONet_dashboard
>>> GONet_dashboard.run()
"""

from GONet_Wizard.GONet_dashboard.src.run_app import run