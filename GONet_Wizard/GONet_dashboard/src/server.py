"""
Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance for the GONet Dashboard.

This module initializes:

- a :class:`flask.Flask` server named ``GONet_dashboard``,
- a `Dash` app instance that uses this server and loads assets from the package's static folder,
- the HTML template for the Dash app.

The `app` object is fully initialized and can be used as a WSGI entry point for deployment tools such as Gunicorn.

These objects are imported by the rest of the dashboard system, including the main entry point
(:mod:`GONet_Wizard.GONet_dashboard.src.app`) and the callback definitions in :mod:`callbacks`.

"""

from flask import Flask
from dash import Dash
import GONet_Wizard.settings as settings

#: Flask server used as the backend for the Dash app.
server = Flask('GONet_dashboard')

#: The Dash app instance.
app = Dash(server=server, assets_folder=settings.STATIC)

from GONet_Wizard.GONet_dashboard.src.layout import layout
app.layout = layout

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="/assets/css/style.css">
        <script src="/assets/js/launcher.js"></script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''