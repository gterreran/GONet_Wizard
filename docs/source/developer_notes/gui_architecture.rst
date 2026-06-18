GUI Architecture
================

The GONet Wizard graphical interface is designed as a frontend to the same
command system used by the command-line interface.

The GUI does not reimplement the core operations. Instead, it collects user
input, translates that input into command-compatible arguments, and delegates
execution to the same handlers used by the CLI.

This design keeps the GUI and CLI aligned and reduces the risk that the two
interfaces behave differently over time.

See also:

* :doc:`GUI Guide <../gui_guide/index>`
* :doc:`CLI Reference <../cli_reference/index>`
* :doc:`Tools guide <../tools/index>`
* :doc:`UI runtime developer notes <ui_runtime>`


Key Code Paths
--------------

The GUI architecture spans the form layer, command dispatch layer, and runtime
presentation layer.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File
     - Role
   * - ``GONet_Wizard/gui/web.py``
     - Flask blueprint for launcher pages, command forms, and the ``/run`` endpoint.
   * - ``GONet_Wizard/commands/parser_builder.py``
     - Builds the parser tree and attaches wrapped handlers.
   * - ``GONet_Wizard/commands/ui_bridge.py``
     - Converts handler return values into preview publishes and window requests.
   * - ``GONet_Wizard/ui/server.py``
     - Creates the unified Flask server hosting launcher and preview routes.
   * - ``GONet_Wizard/ui/windows.py``
     - Defines ``WindowSpec`` and the managed window registry.
   * - ``GONet_Wizard/ui/runtime.py``
     - Guards the PyWebview event loop and server lifecycle.

Important classes and functions include ``CommandSpec``, ``ParserSpec``,
``WindowRequest``, ``PublishRequest``, ``WindowSpec``,
``payload_to_argv_with_parser()``, ``realize_ui_result()``, and
``WINDOWS.ensure()``.

For generated API documentation, see :doc:`GUI API reference <../api_reference/gui>`,
:doc:`UI runtime API reference <../api_reference/ui>`, and :doc:`commands API reference <../api_reference/commands>`.

Form-to-Command Anchors
-----------------------

The most important GUI form path is:

.. code-block:: text

   GONet_Wizard/gui/web.py::command_page()
        |
        v
   templates/form_page.html + templates/forms/<command>.html
        |
        v
   GONet_Wizard/gui/web.py::run_command()
        |
        v
   GONet_Wizard/gui/web.py::payload_to_argv_with_parser()
        |
        v
   argparse parser from get_cli_parser()
        |
        v
   args.handler(args)

This path is why GUI forms should stay aligned with argparse destination names.
The form layer should collect input, not duplicate command behavior.

Design Goals
------------

The GUI architecture is built around a few core goals:

* Provide a user-friendly interface for common workflows.
* Reuse the same command definitions used by the CLI.
* Avoid duplicating business logic between interfaces.
* Keep command forms declarative and maintainable.
* Centralize window and runtime management.
* Allow commands to return GUI-friendly previews when appropriate.

At a high level, the GUI should feel like an application, while internally
remaining a thin layer over the command infrastructure.

High-Level Flow
---------------

A typical GUI command follows this flow:

.. code-block:: text

   Launcher button
        |
        v

   Command form
        |
        v

   Submitted form payload
        |
        v

   argparse-compatible argument list
        |
        v

   Command parser
        |
        v

   Command handler
        |
        v

   GUI result handling
        |
        +--> preview window
        |
        +--> Dash application window
        |
        +--> interactive extraction window
        |
        +--> status or error response

The important architectural point is that command execution passes through the
same parser and handler stack used by the command-line interface.

Launcher
--------

The launcher is the user's entry point into the graphical interface.

It presents the main available tools:

* Show Image
* Show Metadata
* Extract Region
* Dashboard

Each launcher button opens a form page for the corresponding command.

The launcher itself does not perform image processing, metadata extraction, or
data analysis. Its responsibility is routing the user to the appropriate GUI
form.

For the user-facing launcher documentation, see :doc:`GUI launcher guide <../gui_guide/launcher>`.

Command Forms
-------------

Command forms collect the inputs needed to run GONet Wizard operations.

Examples include:

* Input files or folders.
* Channel selections.
* Extraction shape parameters.
* Output filenames.
* Output formats.
* Dashboard input directories.

The form pages are intentionally close to the command-line interface. GUI
fields correspond to command arguments whenever possible.

This makes it easier to:

* Keep the GUI and CLI behavior consistent.
* Reuse validation logic.
* Document GUI and CLI usage in parallel.
* Add new GUI-accessible commands with minimal duplication.

Form Submission
---------------

When a GUI form is submitted, the submitted payload is converted into an
argument list compatible with the command parser.

Conceptually:

.. code-block:: text

   GUI fields
        |
        v

   ["show", "file1.jpg,file2.jpg", "--blue", "--green", "--red"]

        |
        v

   argparse parser

The parser then produces the same parsed arguments object that would have been
created by a command-line invocation.

This keeps command behavior centralized in the command handlers rather than in
the GUI layer.

Relationship with Command Specifications
----------------------------------------

The GUI is closely tied to the command specification system.

Command definitions describe:

* Command names.
* Argument definitions.
* Defaults.
* Help text.
* Handler functions.
* GUI visibility and form behavior.

The GUI uses this information to expose commands through form pages while
preserving the same underlying command semantics used by the CLI.

When a new command is added to the command registry, it can usually be exposed
through the GUI by ensuring that its arguments are described in a way the form
system can render.

Command Handlers
----------------

Command handlers are responsible for performing the actual work.

The GUI should not contain command-specific processing logic such as:

* Reading GONet files.
* Splitting Bayer channels.
* Computing extraction results.
* Loading dashboard data.
* Building Plotly figures.

Those responsibilities belong to the command handlers and lower-level modules.

The GUI layer should only:

* Collect input.
* Submit the command.
* Display the result.
* Report errors in a user-friendly way.

GUI Result Handling
-------------------

Some commands are naturally terminal-oriented, while others produce rich visual
outputs.

GONet Wizard uses GUI result handling to adapt command outputs to graphical
windows when the command is launched through the GUI.

Examples include:

* Opening an image inspection preview.
* Opening a metadata preview.
* Launching the interactive extraction GUI.
* Starting the dashboard in a dedicated window.

This result-handling layer allows command handlers to remain reusable while
still supporting a polished GUI experience.

Preview Windows
---------------

Image and metadata inspection commands can produce preview windows.

A preview window is a graphical wrapper around HTML output generated by the
command. This allows visually rich results to be displayed in the GUI without
changing the underlying command implementation.

Preview windows are especially useful for commands such as:

* ``show``
* ``show_meta``

These commands can be launched from either interface, but the GUI presents
their outputs in dedicated windows.

Interactive Tools
-----------------

Some GUI actions open interactive applications rather than static previews.

For example:

* The extraction command may open the interactive extraction GUI.
* The dashboard command launches the dashboard application.

These tools are still reached through the command/form system, but their final
result is an interactive application window rather than a static preview.

Window Management
-----------------

The GUI may open several types of windows:

* The launcher window.
* Command form windows.
* Preview windows.
* Dash application windows.
* Interactive extraction windows.

Window creation is centralized in the UI runtime rather than being handled
independently by each command.

This is important because desktop GUI execution must respect the constraints
of the underlying webview runtime. In particular, the application should avoid
letting separate subsystems independently create and manage incompatible
window lifecycles.

At a high level, commands request windows through the GUI/runtime layer, and
the runtime is responsible for creating, focusing, and managing those windows.

For the full lifecycle of the Flask server, PyWebview event loop, window
specifications, preview routing, and dashboard windows, see
:doc:`UI runtime developer notes <ui_runtime>`.

Relationship with Dash Applications
-----------------------------------

Some GONet Wizard tools are implemented as Dash applications.

The GUI does not embed Dash logic directly into normal form pages. Instead,
Dash applications are launched through the runtime so that they can run in
their own application context and be displayed in a desktop window.

This keeps the launcher and form system lightweight while still allowing
specialized interactive applications to exist where they are useful.

Static Assets and Templates
---------------------------

The GUI uses shared templates, stylesheets, JavaScript, and image assets.

This keeps the visual identity consistent across:

* The launcher.
* Command forms.
* Preview windows.
* Interactive tools.

When adding new GUI pages, prefer reusing existing templates and CSS classes
instead of introducing inline styles or command-specific layout rules.

Adding a GUI-Accessible Command
-------------------------------

A new GUI-accessible command should generally follow this pattern:

#. Define the command using the command specification system.
#. Ensure arguments are described in a GUI-renderable way.
#. Implement the command handler independently of the GUI.
#. Decide what the command should return when launched from the GUI.
#. Add or update any templates only when the generic form system is not enough.
#. Add user-facing GUI documentation.

The command handler should remain usable from the command line.

If a command requires a custom interactive window, the command should integrate
with the UI runtime rather than creating windows directly.

Common Pitfalls
---------------

Avoid duplicating command logic inside GUI callbacks.

Avoid adding GUI-only behavior that causes the same command to produce
different scientific or data-processing results from the CLI.

Avoid creating windows directly from unrelated modules.

Avoid adding inline styles when the shared stylesheet can be extended instead.

Avoid making a command depend on GUI state if it should also work from the CLI.

Summary
-------

The GONet Wizard GUI is best understood as a graphical command frontend.

It provides a friendly desktop interface, but the actual processing remains in
the shared command and library layers.

This architecture keeps the project maintainable because improvements to the
core command implementation automatically benefit both the GUI and the CLI.
