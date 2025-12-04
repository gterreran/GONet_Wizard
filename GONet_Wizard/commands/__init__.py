"""
Command Definitions for the GONet Wizard CLI
============================================

This package defines all command-line commands available in the GONet Wizard
interface. Each command is implemented in a dedicated module (e.g. ``show``,
``show_meta``, ``extract``), and each exposes a :class:`~GONet_Wizard.commands.cli_core.CommandSpec`
object describing its CLI signature.

The package also declares a top-level :class:`~GONet_Wizard.commands.cli_core.ParserSpec`
named :data:`PARSER`, which the centralized parser builder uses to construct the
entire command hierarchy dynamically. This design ensures that:

1. **Command registration is fully declarative.**
   All commands are discovered through :data:`COMMANDS` and the nested structure
   defined in :data:`PARSER`, rather than through hand-written argparse logic.
2. **Subcommand groups (nested parsers) are modular.**
   The ``connect`` command is implemented as a group of subcommands housed in the
   ``connect_commands`` subpackage. Its parser specification is referenced inside
   :data:`PARSER` under the ``subparsers`` key, allowing deeper CLI trees to be
   built automatically.
3. **Individual command modules remain simple and self-contained.**
   A command module only defines:

       - a :class:`CommandSpec` describing its arguments
       - a handler function (usually ``cli_handler(args)``)
       - any reusable logic specific to that command
       
   The parser builder takes care of wiring these into the global CLI.

Structure
---------

Top-level commands are listed in :data:`COMMANDS`, which includes:

    - :mod:`GONet_Wizard.commands.show`
    - :mod:`GONet_Wizard.commands.show_meta`
    - :mod:`GONet_Wizard.commands.extract`
    - :mod:`GONet_Wizard.commands.run_dashboard`
    - :mod:`GONet_Wizard.commands.connect`

Nested commands for ``connect`` are defined in:

    - :mod:`GONet_Wizard.commands.connect_commands`

The :data:`PARSER` object describes the root parser level and delegates the
``connect`` subparser group to the ``connect_commands`` package.

Integration
-----------

The GONet Wizard CLI driver (``GONet_Wizard.cli``) calls the centralized parser
builder, passing this package to construct the full command tree. At runtime,
each parsed command resolves to a ``handler(args)`` function attached via
``set_defaults`` during registration.

In summary, this package serves as the declarative registry for the entire
GONet Wizard command-line interface, keeping the CLI structure modular,
maintainable, and easy to extend.

Constants
---------
:data:`COMMANDS` : :class:`tuple` of command modules
    Top-level commands available in the GONet Wizard CLI.
:data:`PARSER` : :class:`~GONet_Wizard.commands.cli_core.ParserSpec`
    Parser specification for the GONet Wizard CLI.
"""


from GONet_Wizard.commands import show, show_meta, extract, run_dashboard, connect, build_full_array
from GONet_Wizard.commands import connect_commands
from .cli_core import ParserSpec

COMMANDS = (show, show_meta, extract, run_dashboard, connect, build_full_array)

PARSER = ParserSpec(
    dest="command",
    help="Top-level commands for GONet Wizard CLI.",
    args={
        "commands": COMMANDS,
        "subparsers": [
            {
                "parser_name": "connect",
                "package": connect_commands,
            }
        ],
    },
)
