"""
Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance used by the GONet extraction GUI.

This module initializes:

- a :class:`flask.Flask` backend server for the Dash application named ``GONet extraction GUI``,
- the Dash app instance used to build the interactive GUI.

"""


from flask import Flask
from dash import Dash

#: Flask server used as the backend for the Dash app.
server = Flask('GONet extraction GUI')

#: The Dash app instance.
app = Dash(server=server)