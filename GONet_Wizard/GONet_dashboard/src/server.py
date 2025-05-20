"""
Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance for the GONet Dashboard.

This module initializes:

- a :class:`flask.Flask` server named ``GONet_dashboard``,
- a `Dash` app instance that uses this server and loads assets from the local ``assets/`` folder,
- and the dashboard layout, which is now assigned here at startup.

The `app` object is fully initialized and can be used as a WSGI entry point for deployment tools such as Gunicorn.

These objects are imported by the rest of the dashboard system, including the main entry point
(:mod:`GONet_Wizard.GONet_dashboard.src.app`) and the callback definitions in :mod:`callbacks`.

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

from GONet_Wizard.GONet_dashboard.src.layout import layout
app.layout = layout