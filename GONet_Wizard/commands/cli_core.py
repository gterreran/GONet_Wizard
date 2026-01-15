# GONet_Wizard/commands/cli_core.py

"""
Command-Line Interface Core Compatibility Layer
===============================================

This module serves as a compatibility shim for the GONet Wizard command-line
infrastructure. Historically, it hosted CLI specifications, input expansion
helpers, parser construction utilities, and UI preview integration in a single
location.

As the CLI architecture evolved, these responsibilities were split into
dedicated modules to improve separation of concerns and maintainability:

- :mod:`GONet_Wizard.commands.specs`
- :mod:`GONet_Wizard.commands.inputs`
- :mod:`GONet_Wizard.commands.ui_bridge`
- :mod:`GONet_Wizard.commands.parser_builder`

This module re-exports the public API from those modules to preserve backward
compatibility and avoid widespread changes to existing imports.

Constants
---------
None

Classes
-------
:class:`ParserSpec`
    Declarative specification for CLI parser groups.
:class:`CommandSpec`
    Declarative specification for individual CLI commands.
:class:`ExpandFilenames`
    :class:`argparse.Action` for expanding CLI file inputs.
:class:`ExtensionFilterError`
    Exception raised when extension-based filtering yields no files.
:class:`PublishRequest`
    Request to publish HTML preview content.
:class:`WindowRequest`
    Request to open or focus a UI window.

Functions
---------
:func:`expand_inputs`
    Expand CLI file tokens into concrete filesystem paths.
:func:`filter_by_ext`
    Filter file paths by allowed extensions.
:func:`maybe_present_ui_result`
    Realize UI results and start the webview loop if needed.
:func:`realize_ui_result`
    Normalize and apply UI result(s).
:func:`wrap_handler_for_ui`
    Wrap a CLI handler to support UI result emission.
:func:`build_subparser`
    Recursively construct an argparse subparser tree.
:func:`register_simple_subcommand`
    Register a leaf command on a subparser group.

"""

from __future__ import annotations

# Specs
from GONet_Wizard.commands.specs import ParserSpec, CommandSpec

# Input expansion helpers
from GONet_Wizard.commands.inputs import (
    ExpandFilenames,
    ExtensionFilterError,
    expand_inputs,
    filter_by_ext,
)

# UI result types + wrappers
from GONet_Wizard.commands.ui_bridge import (
    PublishRequest,
    WindowRequest,
    maybe_present_ui_result,
    realize_ui_result,
    wrap_handler_for_ui,
)

# Parser construction
from GONet_Wizard.commands.parser_builder import (
    build_subparser,
    register_simple_subcommand,
)
