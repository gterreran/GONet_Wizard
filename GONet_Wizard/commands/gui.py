"""
GONet GUI Launcher
============================

Entry point for launching the GONet GUI application.

This module imports the GUI launcher and provides a top-level function to start the GUI.
The GUI allows users to interactively work with GONet data through a graphical interface.


**Constants**

- :data:`COMMAND` : :class:`~GONet_Wizard.commands.cli_core.CommandSpec` object
  for the `gui` command.

**Functions**

- :func:`launch_GONet_gui` : Launch the GONet GUI application.

"""

from GONet_Wizard.gui_launcher.launcher import start
from GONet_Wizard.commands.cli_core import CommandSpec
import argparse


COMMAND = CommandSpec(
    name="gui",
    help="Launch the GONet GUI.",
    args=[],
)

def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler for the `gui` command.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments (not used).
    
    Returns
    -------
    None

    """


    start()