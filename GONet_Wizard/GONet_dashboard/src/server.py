"""
Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance for the GONet Dashboard.

This module initializes:

- a :class:`flask.Flask` server named "GONet_dashboard", and
- a `Dash <https://dash.plotly.com/>`_ `app` that uses this server and loads assets from the local `assets/` folder.

These objects are imported by the rest of the dashboard system (e.g. :mod:`GONet_Wizard.GONet_dashboard.src.app`).
"""

from flask import Flask
from dash import Dash
import os

#: Flask server used as the backend for the Dash app.
server = Flask('GONet_dashboard')

#: Path to the `assets/` directory for Dash (CSS, images, etc.)
this_dir = os.path.dirname(__file__)
assets_path = os.path.join(this_dir, 'assets')

#: The Dash app instance.
app = Dash(server=server, assets_folder=assets_path)
