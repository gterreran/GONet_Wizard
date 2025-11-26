"""
Subcommands for the ``connect`` Command
=======================================

This package defines the nested subcommands available under the top-level
``connect`` command of the GONet Wizard CLI. These subcommands perform remote
operations on a GONet device over SSH, such as triggering imaging or terminating
running processes.

The package integrates with the centralized CLI parser through the
:data:`PARSER` object, which is a :class:`~GONet_Wizard.commands.cli_core.ParserSpec`
describing this subcommand group. The main ``connect`` command (defined in
``GONet_Wizard.commands.connect``) delegates its nested parsing to this package.

Parser Specification
--------------------

The :data:`PARSER` defined here specifies the following:

- ``dest="connect_subcommand"``  
  The argparse attribute where the chosen subcommand name will be stored.
- ``help``  
  The help text shown when running ``GONet_Wizard connect -h``.
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