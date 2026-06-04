"""
GONet Connect Command.
========================

This module defines the experimental ``connect`` command specification.

The remote-camera workflow is currently deferred and intentionally not
registered in the public GONet Wizard command tree. The :data:`COMMAND`
constant is kept so the SSH workflow can be revived later or split into a
separate remote-control package without rebuilding the command specification.

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