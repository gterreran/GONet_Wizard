"""
Subcommands for the ``connect`` Command
=======================================

This package contains the experimental remote-camera helpers originally planned
for a nested ``connect`` command. These helpers perform remote operations on a
GONet device over SSH, such as triggering imaging or terminating running
processes.

The remote-camera workflow is currently deferred and intentionally not
registered in the public GONet Wizard command tree. The :data:`PARSER` object is
kept here so the workflow can be revived later or moved into a separate remote
control package without reconstructing the command specification from scratch.

Parser Specification
--------------------

The :data:`PARSER` defined here specifies the following:

- ``dest="connect_subcommand"``  
  The argparse attribute where the chosen subcommand name will be stored.
- ``help``  
  The help text that would be shown if the experimental ``connect`` group were registered.
- ``args={"commands": COMMANDS}``  
  Registers the ``snap`` and ``terminate`` command modules—each of which provides
  a :class:`~GONet_Wizard.commands.cli_core.CommandSpec` and a CLI handler.

This declarative structure allows the CLI builder to recursively attach this
subpackage under the main ``connect`` command with no manual argparse wiring.

"""

from GONet_Wizard.commands.cli_core import ParserSpec
from . import snap, terminate

COMMANDS = (snap, terminate)

PARSER = ParserSpec(
    dest="connect_subcommand",
    help="SSH Connection Utilities for GONet remote operations.",
    args={
        "commands": COMMANDS,
    },
)