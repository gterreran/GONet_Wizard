"""
GONet Wizard Dashboard Application Entry Point.

This module initializes the GONet Wizard `Dash <https://dash.plotly.com/>`_ application
and performs environment validation before interactive components are used.

Key responsibilities:

- Loads and validates critical environment variables through :class:`DashboardConfig`
- Assigns data and image paths to the shared `env` module used across the dashboard
- Imports and registers all callback functions to enable interactivity
- Ensures that configuration logic is only executed when explicitly called (e.g., at launch)

This script is suitable as the WSGI entry point for deployment scenarios (e.g., with Gunicorn),
since the Dash `app` object is imported and layout is assigned elsewhere (in `server.py`).

By isolating configuration and callback registration inside the :func:`config_app` function,
this design avoids triggering I/O or environment prompts during testing or static analysis.
"""

from GONet_Wizard.settings import DashboardConfig

def config_app():
    """
    Configure the GONet Dashboard app by performing environment validation,
    assigning layout paths, and registering interactive callbacks.

    This function should be explicitly called during app startup to avoid
    environment prompts at import time. It handles the following setup tasks:

    - Loads the dashboard configuration using :class:`DashboardConfig`, which prompts
      for required environment variables like ``GONET_ROOT`` and optionally ``GONET_ROOT_IMG``.
    - Populates the shared `env` module with the resolved paths so they can be accessed
      by plotting, filtering, and I/O logic across the dashboard.
    - Registers all Dash callback functions by importing :mod:`callbacks`.

    This function is safe to skip during automated testing or CLI-only workflows that
    do not require the full Dash app stack.

    Constants
    ---------

    DASHBOARD_DATA_PATH : :class:`pathlib.Path`
        Loaded from the initialized :class:`GONet_Wizard.settings.DashboardConfig`.
    GONET_IMAGES_PATH : :class:`pathlib.Path` or :class:`None`
        Loaded from the initialized :class:`GONet_Wizard.settings.DashboardConfig`.
        
    """
    config = DashboardConfig()

    # Optionally store config globally if needed in callbacks
    import GONet_Wizard.GONet_dashboard.src.env as env
    env.DASHBOARD_DATA_PATH = config.dashboard_data_path
    env.GONET_IMAGES_PATH = config.gonet_images_path

    from GONet_Wizard.GONet_dashboard.src import callbacks
