"""
GONet Connect Command.
========================

This module defines the `connect` command for the GONet Wizard CLI.
The :data:`COMMAND` constant is defined here, which parses the
GONet device IP address as an argument.

Constants
---------
- :data:`COMMAND` : :class:`~GONet_Wizard.commands.cli_core.CommandSpec` object
  for the `connect` command.

"""

from GONet_Wizard.commands.cli_core import CommandSpec

COMMAND = CommandSpec(
    name="connect",
    help="SSH Connection Utilities for GONet Remote Access.",
    args=[
        {
            "flags": ["gonet_ip"],
            "help": "IP address of the GONet device to connect to."
        }
    ]
)