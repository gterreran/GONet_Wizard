"""
WSGI Entry Point for Deploying the GONet Wizard Dashboard.

This module serves as the WSGI-compatible entry point for production deployment
of the GONet Dashboard application. It is designed to be used with WSGI servers such as:

- Gunicorn (`gunicorn GONet_Wizard.GONet_dashboard.src.wsgi:application`)
- uWSGI
- mod_wsgi (Apache)

Responsibilities
----------------
- Imports the initialized `Dash` app instance from :mod:`server`
- Runs the environment-aware configuration via :func:`config_app`
- Exposes the `Flask` server instance as `application`, as expected by WSGI

The call to :func:`config_app` ensures that all necessary environment variables
are loaded and all callbacks are registered before serving begins.
"""

from GONet_Wizard.GONet_dashboard.src.server import app
from GONet_Wizard.GONet_dashboard.src.app import config_app

config_app()  # Ensures layout, callbacks, and env paths are configured before WSGI serves

#: The WSGI-compatible Flask server instance
application = app.server  # WSGI servers look for this variable by default
