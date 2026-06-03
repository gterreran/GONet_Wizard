# GONet_Wizard/commands/__init__.py

"""
Command Definitions for the GONet Wizard CLI and GUI
====================================================

This package is the declarative registry for all *user-invoked* entry points in
GONet Wizard, supporting both traditional command-line execution and GUI-backed
workflows (PyWebview + a unified local UI server).

Each command is implemented in a dedicated module (e.g. :mod:`.show`,
:mod:`.show_meta`, :mod:`.run_dashboard`) and exposes a
:data:`COMMAND` object of type :class:`~GONet_Wizard.commands.specs.CommandSpec`
describing its CLI signature. At runtime, the parser infrastructure wires these
specs into an :class:`argparse.ArgumentParser` tree and dispatches to a handler.

Beyond the CLI, commands can optionally return structured UI results (preview
publishes, window-open requests, or both). This enables a single command
implementation to work in:

- **terminal-only mode** (print/side effects only), and/or
- **GUI mode** (open windows and publish HTML previews via the unified UI server)

Infrastructure Overview
-----------------------

The command system is split into focused modules that together provide a
declarative, extensible command tree with optional UI presentation:

- :mod:`GONet_Wizard.commands.specs`
  Defines the declarative models :class:`~GONet_Wizard.commands.specs.CommandSpec`
  and :class:`~GONet_Wizard.commands.specs.ParserSpec`.

- :mod:`GONet_Wizard.commands.inputs`
  Provides CLI input normalization utilities such as :class:`.ExpandFilenames`,
  :func:`.expand_inputs`, and :func:`.filter_by_ext`.

- :mod:`GONet_Wizard.commands.parser_builder`
  Constructs the full parser hierarchy from :data:`PARSER` and command specs via
  :func:`~GONet_Wizard.commands.parser_builder.build_subparser`.

- :mod:`GONet_Wizard.commands.ui_bridge`
  Defines the UI result protocol (:class:`~GONet_Wizard.commands.ui_bridge.PublishRequest`,
  :class:`~GONet_Wizard.commands.ui_bridge.WindowRequest`) and wrappers that
  normalize and realize handler return values, enabling commands to publish
  previews and request managed windows.

- :mod:`GONet_Wizard.commands.cli_core`
  A compatibility shim that re-exports the public API from the modules above to
  avoid churn in legacy imports.

Declarative Command Tree
------------------------

This package declares the root :data:`PARSER` object (a
:class:`~GONet_Wizard.commands.specs.ParserSpec`) describing the top-level CLI
group. The centralized parser builder consumes :data:`PARSER` to build the
complete command hierarchy dynamically.

Top-level commands are collected in :data:`COMMANDS`. Nested command groups are
registered as subparser packages (e.g., the ``connect`` group delegates to the
:mod:`GONet_Wizard.commands.connect_commands` subpackage via :data:`PARSER`).

Available Commands
------------------

:mod:`GONet_Wizard.commands.show`
    Visualize one or more GONet files and channels using Plotly.
:mod:`GONet_Wizard.commands.show_meta`
    Extract and display GONet file metadata as text or HTML.
:mod:`GONet_Wizard.commands.extract`
    Extract pixel counts from GONet files using configurable ROI shapes.
:mod:`GONet_Wizard.commands.run_dashboard`
    Launch the interactive Dash-based GONet Wizard dashboard in a managed window.
:mod:`GONet_Wizard.commands.connect`
    Command group for connecting to a GONet device (subcommands in :mod:`.connect_commands`).
:mod:`GONet_Wizard.commands.build_full_array`
    Build or process full-array products from GONet inputs.
:mod:`GONet_Wizard.commands.gui`
    Launch the unified GUI launcher window.

Constants
---------
:data:`COMMANDS` : :class:`tuple`
    Tuple of top-level command modules registered under the root parser.
:data:`PARSER` : :class:`~GONet_Wizard.commands.specs.ParserSpec`
    Root parser specification defining the command hierarchy for the CLI/GUI.
"""

# connect is intentionally not registered yet.
# The remote-camera workflow is experimental and may become
# a separate package or optional extension later.
# "GONet_Wizard.commands.connect_commands",

from GONet_Wizard.commands import show, show_meta, extract, run_dashboard, build_full_array, gui, connect
#from GONet_Wizard.commands import connect_commands
from .cli_core import ParserSpec

COMMANDS = (show, show_meta, extract, run_dashboard, build_full_array, gui) #connect

PARSER = ParserSpec(
    dest="command",
    help="Top-level commands for GONet Wizard CLI.",
    args={
        "commands": COMMANDS,
        # "subparsers": [
        #     {
        #         "parser_name": "connect",
        #         "package": connect_commands,
        #     }
        # ],
    },
)
