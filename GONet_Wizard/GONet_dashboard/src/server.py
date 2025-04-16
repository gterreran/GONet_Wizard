"""
Defines the Flask server and :dashdoc:`Dash <>` app instance for the GONet Dashboard.

This module initializes:
- a :class:`flask.Flask` server named "GONet_dashboard", and
- a :dashdoc:`Dash <>` `app` that uses this server and loads assets from the local `assets/` folder.

These objects are imported by the rest of the dashboard system (e.g. `app.py`).
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
