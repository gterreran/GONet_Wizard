"""
`GONet_Wizard <https://github.com/gterreran/GONet_Wizard/>`_: A toolkit for analyzing and visualizing GONet sky monitoring data.

This package provides tools for:

- Parsing and decoding raw GONet camera files
- Visualizing the image data
- Monitoring the data from multi-epoch campaigns
- Deploying dashboards and documentation
- Centralized configuration management via environment-aware settings

The package also initializes its environment-dependent configuration
via the :mod:`GONet_Wizard.settings` module. This module defines and validates
the environment variables required to run the GONet tools and dashboard components.
Settings are accessed dynamically to ensure runtime flexibility and testability.
"""

from __future__ import annotations
from GONet_Wizard._version import __version__
import GONet_Wizard.settings