Command System
==============

The GONet Wizard command system is the shared execution backbone used by both
the command-line interface and the graphical interface.

Commands are declared once, registered in the command package, converted into an
``argparse`` parser tree, and dispatched through command handlers. GUI forms use
the same parser and handlers as terminal invocations, so the GUI remains a
frontend over the same command infrastructure rather than a separate
implementation.

This page describes the internal command architecture and highlights the files
and functions most relevant to contributors.

See also:

* :doc:`GUI architecture developer notes <gui_architecture>`
* :doc:`UI runtime developer notes <ui_runtime>`
* :doc:`CLI Reference <../cli_reference/index>`
* :doc:`GUI Guide <../gui_guide/index>`


Key Code Paths
--------------

The command system is implemented primarily in these files:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File
     - Important objects and functions
   * - ``GONet_Wizard/commands/specs.py``
     - ``CommandSpec``, ``ParserSpec``
   * - ``GONet_Wizard/commands/__init__.py``
     - ``COMMANDS``, root ``PARSER``
   * - ``GONet_Wizard/commands/parser_builder.py``
     - ``build_subparser()``, ``register_simple_subcommand()``
   * - ``GONet_Wizard/commands/ui_bridge.py``
     - ``PublishRequest``, ``WindowRequest``, ``wrap_handler_for_ui()``
   * - ``GONet_Wizard/commands/inputs.py``
     - ``ExpandFilenames``, ``expand_inputs()``, ``filter_by_ext()``
   * - ``GONet_Wizard/commands/smart_parser.py``
     - ``SmartArgumentParser``, ``set_current_argv()``
   * - ``GONet_Wizard/cli.py``
     - ``main()``, global flag pre-parsing, parse-time GUI form routing

For generated API documentation, see :doc:`commands API reference <../api_reference/commands>`.

Primary Execution Path
----------------------

The normal CLI execution path is anchored by these functions and objects:

.. code-block:: text

   GONet_Wizard.cli.main()
        |
        v
   GONet_Wizard.commands.cli_core.build_subparser()
        |
        v
   GONet_Wizard.commands.parser_builder.register_simple_subcommand()
        |
        v
   GONet_Wizard.commands.ui_bridge.wrap_handler_for_ui()
        |
        v
   <command_module>.cli_handler(args)

The command module owns the command-specific orchestration. The parser builder
owns argument wiring. The UI bridge owns optional presentation behavior.

Design Goals
------------

The command system is designed to:

* Keep command definitions declarative.
* Centralize parser construction.
* Avoid duplicating argument wiring across command modules.
* Make each command usable from the terminal.
* Allow GUI workflows to reuse the same command handlers.
* Allow command handlers to optionally request UI presentation.
* Keep input expansion and validation reusable across commands.
* Preserve backward compatibility while the command architecture evolves.

The core idea is simple:

.. code-block:: text

   CommandSpec / ParserSpec
        |
        v

   parser_builder.build_subparser()
        |
        v

   argparse command tree
        |
        v

   wrapped command handler
        |
        v

   cli_handler(args)
        |
        +--> terminal behavior
        |
        +--> UI result protocol

Main Modules
------------

The command system is split across several focused modules.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Module
     - Responsibility
   * - ``commands/specs.py``
     - Defines ``CommandSpec`` and ``ParserSpec``.
   * - ``commands/__init__.py``
     - Registers public command modules and defines the root ``PARSER``.
   * - ``commands/parser_builder.py``
     - Builds the recursive ``argparse`` parser tree from the declarative specs.
   * - ``commands/ui_bridge.py``
     - Wraps handlers and realizes optional UI result objects.
   * - ``commands/inputs.py``
     - Expands files, folders, wildcards, and comma-separated input tokens.
   * - ``commands/smart_parser.py``
     - Replaces ``argparse`` exits with classified parse exceptions.
   * - ``commands/argparse_errors.py``
     - Defines parse-error categories and the ``CliParseError`` model.
   * - ``commands/cli_core.py``
     - Compatibility re-export layer for the command-system public API.
   * - ``cli.py``
     - Top-level CLI entry point.

Specification Models
--------------------

The declarative command models are defined in ``commands/specs.py``.

``CommandSpec``
~~~~~~~~~~~~~~~

``CommandSpec`` describes a single executable command.

A command specification contains:

* ``name``: command name.
* ``help``: short help string.
* ``args``: a list of argument dictionaries passed to
  ``ArgumentParser.add_argument``.

A typical command module exposes a module-level ``COMMAND`` object and a
``cli_handler(args)`` function.

Conceptually:

.. code-block:: python

   COMMAND = CommandSpec(
       name="example",
       help="Run an example command.",
       args=[
           {
               "flags": ["input"],
               "nargs": "+",
               "help": "Input files.",
           },
           {
               "flags": ["--debug"],
               "action": "store_true",
               "default": False,
               "help": "Enable debug mode.",
           },
       ],
   )

   def cli_handler(args):
       ...

``ParserSpec``
~~~~~~~~~~~~~~

``ParserSpec`` describes a command group.

It defines:

* ``dest``: the namespace attribute where the selected command is stored.
* ``help``: help text for the subparser group.
* ``args``: a configuration dictionary containing registered commands and
  optional nested subparser groups.

The root command group is defined in ``commands/__init__.py`` as ``PARSER``.

Command Registry
----------------

The public command registry lives in ``commands/__init__.py``.

That module imports the command modules that should be available to users and
collects them into ``COMMANDS``.

The root ``PARSER`` then exposes those commands to the parser builder.

Conceptually:

.. code-block:: python

   COMMANDS = (
       show,
       show_meta,
       extract,
       run_dashboard,
       build_full_array,
       gui,
   )

   PARSER = ParserSpec(
       dest="command",
       help="Top-level commands for GONet Wizard CLI.",
       args={
           "commands": COMMANDS,
       },
   )

A command module can exist in the source tree without being registered in
``COMMANDS``. This is useful for experimental commands that are not yet part of
the public command tree.

Command Modules
---------------

A command module should usually define two things:

``COMMAND``
   Declarative command signature.

``cli_handler(args)``
   Execution entry point called after argument parsing.

The command handler should contain command orchestration logic, but the lower
level scientific or data-processing logic should generally remain in reusable
library modules.

This keeps commands small and focused:

.. code-block:: text

   parse arguments
        |
        v

   normalize inputs
        |
        v

   call reusable implementation
        |
        v

   print output, write files, or return a UI result

Parser Construction
-------------------

Parser construction is implemented in ``commands/parser_builder.py``.

The main functions are:

``build_subparser(parser, package)``
   Recursively builds subparsers from a package-level ``PARSER`` specification.

``register_simple_subcommand(subparsers, cmd)``
   Registers one leaf command by reading ``cmd.COMMAND`` and adding each
   argument specification to an ``argparse`` subparser.

During registration, if the command module defines ``cli_handler``, the parser
builder attaches a wrapped handler using:

.. code-block:: python

   parser.set_defaults(handler=wrap_handler_for_ui(cmd))

This wrapper is what allows normal command handlers to optionally return UI
result objects.

Handler Dispatch
----------------

The top-level CLI entry point is ``cli.py``.

The simplified dispatch flow is:

.. code-block:: text

   cli.main()
        |
        v

   SmartArgumentParser(...)
        |
        v

   cli_core.build_subparser(parser, commands)
        |
        v

   parser.parse_args(argv)
        |
        v

   args.handler(args)

The parser builder attaches ``args.handler`` using ``set_defaults`` when each
command is registered.

If the parsed namespace does not include a handler, the CLI prints help instead
of executing a command.

Compatibility Layer
-------------------

``commands/cli_core.py`` is a compatibility shim.

Earlier versions of the project kept command specs, input expansion, parser
building, and UI preview integration in one module. Those responsibilities were
later split into focused modules, but ``cli_core.py`` still re-exports the
public API.

This allows older imports such as:

.. code-block:: python

   from GONet_Wizard.commands.cli_core import CommandSpec, ExpandFilenames

to keep working while the internal implementation remains better organized.

Input Expansion
---------------

Reusable input normalization lives in ``commands/inputs.py``.

The most important pieces are:

``ExpandFilenames``
   An ``argparse.Action`` that expands user-provided input tokens.

``expand_inputs(tokens)``
   Expands files, directories, glob patterns, and comma-separated lists.

``filter_by_ext(paths, exts)``
   Filters expanded paths by allowed extensions.

``ExtensionFilterError``
   Raised when extension filtering removes all candidate files.

Supported input patterns include:

* explicit file paths,
* non-recursive directory expansion,
* wildcard patterns,
* comma-separated token lists.

This allows commands such as ``show``, ``show_meta``, ``extract``, and
``dashboard`` to share consistent file-handling behavior.

UI-Aware Handler Wrapping
-------------------------

UI-aware handler wrapping is implemented in ``commands/ui_bridge.py``.

The key objects are:

``PublishRequest``
   Request to publish HTML under a preview channel.

``WindowRequest``
   Request to open or focus a managed UI window.

``wrap_handler_for_ui(cmd)``
   Wraps a command ``cli_handler`` so its return value can be interpreted as a
   UI result.

``maybe_present_ui_result()``
   Realizes any requested UI behavior and starts the PyWebview loop when
   windows are needed.

This allows a command handler to return different kinds of values:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Return value
     - Meaning
   * - ``None``
     - No UI action.
   * - ``str``
     - Legacy HTML preview.
   * - ``PublishRequest``
     - Publish HTML without opening a window.
   * - ``WindowRequest``
     - Open or focus a managed window.
   * - ``list`` or ``tuple``
     - Realize multiple UI results.

Because the parser builder wraps handlers automatically, command modules do not
need to call the UI bridge directly unless they want to construct explicit UI
result objects.

Legacy HTML Results
~~~~~~~~~~~~~~~~~~~

For backward compatibility, a handler may return an HTML string.

The UI bridge normalizes that string into a ``WindowRequest`` that:

* publishes the string under a preview channel matching the command name,
* opens ``/view/<command>`` on the unified local UI server.

This pattern is used by commands that generate HTML previews.

Structured Window Results
~~~~~~~~~~~~~~~~~~~~~~~~~

Commands that launch dedicated windows should return ``WindowRequest`` objects
explicitly.

For example, the ``gui`` command returns a request for the launcher window, and
the ``dashboard`` command returns a request for the dashboard window.

Smart Parse Errors
------------------

The standard ``argparse`` behavior is to call ``sys.exit()`` when parsing
fails.

GONet Wizard replaces that behavior with ``SmartArgumentParser`` in
``commands/smart_parser.py``.

``SmartArgumentParser`` raises ``CliParseError`` instead of exiting. The error
is classified using ``ParseErrorKind`` from ``commands/argparse_errors.py``.

The parse-error categories are:

``MISSING_REQUIRED``
   A required argument was omitted.

``UNKNOWN_ARGS``
   One or more tokens were not recognized.

``OTHER``
   Any other parse failure.

This structured error handling allows the top-level CLI to decide whether to
print a normal terminal error or route the user into a GUI form.

Parse-Time GUI Form Routing
---------------------------

The top-level ``cli.py`` file contains a small but important GUI convenience
feature.

If a user invokes a valid command token sequence but omits required arguments,
the CLI can open the corresponding GUI form instead of only printing an error.

For example, a command-only invocation such as:

.. code-block:: text

   GONet_Wizard show

can be classified as a missing-required-argument case. If the invocation
contains only the command tokens, ``cli.py`` calls ``open_command_form()`` from
``ui/launch_forms.py``.

This behavior is deliberately narrow.

It is intended for cases where the user has clearly selected a command but has
not provided the required inputs. Other parse errors, such as unknown flags or
malformed options, continue to behave like normal CLI errors.

Global UI Flags
---------------

``cli.py`` also pre-parses a small set of global flags before full command
parsing.

These include:

``--ui-port``
   Port for the unified local UI server.

``--debug-webview``
   Enable PyWebview debug mode.

``--log-level``
   Configure package logging.

Pre-parsing these flags allows the CLI to preserve UI configuration even when
the full command parse fails and the user is routed to a GUI form.

Representative Commands
-----------------------

This section summarizes a few command modules that illustrate the command
system patterns.

``show_meta``
~~~~~~~~~~~~~

``commands/show_meta.py`` defines the ``show_meta`` command.

Its ``COMMAND`` includes:

* positional ``filenames``,
* an ``--html`` flag.

The ``cli_handler(args)`` function:

#. filters inputs to supported image extensions,
#. calls ``show_metadata(...)``,
#. returns HTML when ``--html`` is set,
#. otherwise prints plain text to the terminal.

This is a good example of a command that can behave as a terminal command or
as a GUI preview source.

``extract``
~~~~~~~~~~~

``commands/extract.py`` defines the ``extract`` command.

Its ``COMMAND`` includes:

* input filenames,
* channel flags,
* extraction shape,
* shape-specific geometry arguments,
* output settings,
* extraction-GUI runtime options.

The ``cli_handler(args)`` has two major branches.

If ``args.shape`` is ``None`` or ``"interactive"``, it launches the Dash-based
interactive extraction GUI and returns a ``WindowRequest``.

Otherwise, it runs direct extraction by calling ``extract_counts_from_GONet()``
and writes JSON or CSV output.

This is a good example of a command that can either perform a batch-style
operation directly or launch a richer interactive interface.

``dashboard``
~~~~~~~~~~~~~

``commands/run_dashboard.py`` defines the ``dashboard`` command.

The handler expands and filters JSON/CSV inputs, starts or reuses the Dash
dashboard server, and returns a ``WindowRequest`` pointing to the dashboard URL.
Image previews are resolved later by the dashboard from the full ``filename``
paths stored in the loaded extraction products.

This is a good example of a command that launches an external interactive app
through the shared UI runtime.

``gui``
~~~~~~~

``commands/gui.py`` defines the ``gui`` command.

The handler ensures that the unified local UI server is running and returns a
``WindowRequest`` for the launcher window.

This command is the direct entry point for opening the graphical launcher from
the terminal.

Adding a New Command
--------------------

To add a new command:

#. Create a new module under ``GONet_Wizard/commands``.
#. Define a module-level ``COMMAND`` object.
#. Define ``cli_handler(args)``.
#. Add the command module to ``COMMANDS`` in ``commands/__init__.py``.
#. Keep reusable processing logic outside the command module when possible.
#. Add tests for parser construction and handler behavior.
#. Add CLI, GUI, or Developer Notes documentation as appropriate.

A minimal command module has this shape:

.. code-block:: python

   from GONet_Wizard.commands.cli_core import CommandSpec

   COMMAND = CommandSpec(
       name="my_command",
       help="Describe what the command does.",
       args=[
           {
               "flags": ["input"],
               "help": "Input path.",
           },
       ],
   )

   def cli_handler(args):
       ...

If the command should open a window, return a ``WindowRequest`` instead of
creating the window directly.

Adding a Nested Command Group
-----------------------------

Nested command groups are represented with ``ParserSpec`` objects and the
``subparsers`` entry in a parser specification.

The parser builder supports recursive construction, so nested workflows can be
represented declaratively.

A nested command group should be added only when the command hierarchy genuinely
benefits from grouping. Otherwise, a simple top-level command is easier for
users and contributors to understand.

Exposing a Command to the GUI
-----------------------------

Most GUI-accessible commands are exposed through the same command specification
used by the CLI.

To make a command GUI-accessible:

#. Ensure its arguments are represented in ``COMMAND.args``.
#. Add or update the corresponding form template when needed.
#. Keep form field names aligned with argparse destination names.
#. Let the GUI ``/run`` route convert the payload into ``argv``.
#. Return a GUI-compatible result if the command should open a window.

The GUI should not call command internals directly when the command can be
reached through the parser.

Best Practices
--------------

Keep command modules thin.

Put reusable data-processing logic in library modules.

Use ``ExpandFilenames`` and ``filter_by_ext`` for consistent file handling.

Use ``CommandSpec`` and ``ParserSpec`` instead of manually adding parser
arguments in multiple places.

Return ``WindowRequest`` or ``PublishRequest`` for UI presentation instead of
creating windows directly.

Avoid GUI-only behavior that changes scientific or data-processing results.

Avoid registering experimental commands in ``COMMANDS`` until they are ready for
public use.

Avoid broad ``try``/``except`` blocks in command handlers unless they preserve
useful user-facing errors.

Summary
-------

The command system lets GONet Wizard define each user-facing operation once and
reuse it across the CLI and GUI.

``CommandSpec`` and ``ParserSpec`` describe the command tree. The parser builder
turns those specifications into ``argparse`` parsers. Handlers perform the work.
The UI bridge interprets optional UI results.

This separation keeps the project maintainable: command behavior remains
centralized, while terminal and GUI presentation layers can evolve around the
same core execution path.
