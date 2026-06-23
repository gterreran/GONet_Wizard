# GONet_Wizard/desktop.py

"""
Desktop GUI Entrypoint
======================

This module provides a GUI-first entry point for packaged desktop builds.  It is
intended for ``[project.gui-scripts]`` and frozen application launchers where the
user starts GONet Wizard by double-clicking an icon rather than typing a command
in a terminal.

The desktop entry point deliberately reuses the existing CLI command system by
invoking the ``gui`` command programmatically.  This keeps the graphical launcher
as a thin distribution layer and preserves all terminal functionality for power
users.
"""

from __future__ import annotations

import sys
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    """
    Launch the GONet Wizard GUI launcher.

    Parameters
    ----------
    argv : sequence of str, optional
        Optional arguments to pass after the implicit ``gui`` command.  When
        ``None``, command-line arguments supplied to the GUI script are used.
        For example, ``gonet-wizard-gui --port 5051`` becomes equivalent to
        ``gonet-wizard gui --port 5051``.

    Returns
    -------
    None
        The function starts the normal GONet Wizard GUI workflow for its side
        effects.
    """
    from GONet_Wizard.cli import main as cli_main

    extra_args = list(sys.argv[1:] if argv is None else argv)
    cli_main(["gui", *extra_args])


if __name__ == "__main__":
    main()
