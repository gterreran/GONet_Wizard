# GONet_Wizard/GONet_dashboard/src/server.py

"""
Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance for the GONet Dashboard.

This module initializes:

- a :class:`flask.Flask` server named ``GONet_dashboard``,
- a `Dash` app instance that uses this server as its backend.

These objects are imported by the rest of the dashboard system, including the main entry point
(:mod:`GONet_Wizard.GONet_dashboard.src.app`) and the callback definitions in :mod:`callbacks`.

"""

from flask import Flask
from dash import Dash
import GONet_Wizard.settings as settings

#: Flask server used as the backend for the Dash app.
server = Flask('GONet_dashboard')

#: The Dash app instance.
app = Dash(server=server, assets_folder=str(settings.STATIC))
