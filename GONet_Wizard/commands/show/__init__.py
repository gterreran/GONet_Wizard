# GONet_Wizard/commands/show/__init__.py

"""
Show Command Package
====================

This package implements the :mod:`GONet_Wizard.commands.show` CLI command, which
renders one or more GONet files as Plotly image panels for interactive inspection.

The command is intentionally split into focused modules:

- :mod:`~GONet_Wizard.commands.show.command` defines the CLI
  :class:`~GONet_Wizard.commands.cli_core.CommandSpec` and the
  :func:`~GONet_Wizard.commands.show.command.cli_handler`.
- :mod:`~GONet_Wizard.commands.show.figure` constructs the Plotly
  :class:`plotly.graph_objects.Figure` used by the command.
- :mod:`~GONet_Wizard.commands.show.layout` provides deterministic layout policy
  (subplot geometry, aspect locking, and zoom-linking payloads).
- :mod:`~GONet_Wizard.commands.show.io` contains optional export helpers (e.g.
  writing the figure to PDF).

The CLI registry expects the command specification and handler to be importable
from the package, so they are re-exported here.

Constants
---------
COMMAND
    The CLI command specification for ``show``.

Functions
---------
cli_handler
    CLI handler that builds the figure and returns the HTML payload for display.
"""

from __future__ import annotations

from .command import COMMAND, cli_handler  # noqa: F401
