"""
HTML Form-Based GUI for the GONet Wizard CLI
============================================

This subpackage provides the HTML and Flask-based form interface used by the
GONet Wizard unified UI runtime. Rather than implementing a separate “GUI
application,” it exposes a lightweight, browser-rendered control surface that
maps directly onto the existing command-line interface.

The GUI is intentionally **CLI-driven**:

- Every GUI action corresponds to a real CLI command
- Form submissions are converted into ``argv`` tokens using argparse metadata
- Commands are parsed and executed through the same handler functions used by
  the terminal CLI
- Any command capable of producing UI output (HTML, preview windows, dashboards)
  can be invoked identically from CLI or GUI

This design ensures a **single source of truth** for command behavior, avoids
logic duplication, and keeps the GUI extensible as new commands are added.

Architecture
------------

The package consists of two main parts:

- **Flask blueprint and routing logic**
  (:mod:`GONet_Wizard.gui.web`)
  - Serves the landing page and per-command form pages
  - Accepts JSON form submissions
  - Translates GUI payloads into ``argv`` lists using argparse introspection
  - Executes commands via their registered CLI handlers

- **Jinja2 templates**
    - Base layout and shared components (e.g. path picker widgets)
    - One form template per command
    - A shared preview shell template reused by the unified UI runtime

The blueprint is registered into the unified Flask server managed by
:mod:`GONet_Wizard.ui.server`, making the GUI available at the same local server
that hosts preview endpoints (``/view/<channel>``).

Design Goals
------------

- **No duplicated command logic**
- **Full parity between CLI and GUI execution paths**
- **Lazy parser construction** to avoid circular imports
- **Declarative extensibility**: adding a new command requires only:
  
  1. A CLI command module with a :class:`~GONet_Wizard.commands.cli_core.CommandSpec`
  2. An optional HTML form template

This package intentionally contains *no application state* and *no business
logic* beyond payload-to-argv translation. It is a thin presentation layer over
the command system.

In short, this subpackage provides a structured, maintainable bridge between
human-friendly HTML forms and the fully declarative GONet Wizard CLI.
"""
