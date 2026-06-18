Contributor Workflows
=====================

This page collects practical workflows for extending GONet Wizard.

It is intentionally more code-oriented than the user-facing guides. The goal is
to connect the architectural notes to the files, classes, and functions a
contributor is most likely to touch.

See also:

* :doc:`command-system developer notes <command_system>`
* :doc:`GUI architecture developer notes <gui_architecture>`
* :doc:`UI runtime developer notes <ui_runtime>`
* :doc:`extractor architecture developer notes <extractor_architecture>`
* :doc:`API Reference <../api_reference/index>`

Choosing the Right Extension Point
----------------------------------

Before editing code, identify which layer the change belongs to.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Goal
     - Start with
   * - Add a new terminal operation
     - ``GONet_Wizard/commands/`` and :doc:`command-system developer notes <command_system>`
   * - Add a GUI form for an existing operation
     - ``GONet_Wizard/gui/web.py``, GUI templates, and :doc:`GUI architecture developer notes <gui_architecture>`
   * - Open or reuse a desktop window
     - ``WindowRequest``, ``WindowSpec``, and :doc:`UI runtime developer notes <ui_runtime>`
   * - Launch a Dash app
     - ``DashLaunchSpec`` and ``ensure_dash_running()``
   * - Add fields to extraction outputs
     - Extractor classes and :doc:`extractor architecture developer notes <extractor_architecture>`
   * - Explain user-facing behavior
     - ``tools/``, ``gui_guide/``, and ``cli_reference/``

Choosing the right layer first helps avoid cross-coupling between commands,
GUI forms, runtime code, and extraction internals.

Adding a New Command
--------------------

A command is usually implemented as a module under
``GONet_Wizard/commands/``.

A minimal command module defines:

* a module-level ``COMMAND`` object,
* a ``cli_handler(args)`` function.

The ``COMMAND`` object is a
``GONet_Wizard.commands.specs.CommandSpec``. It declares the command name,
help text, and argument list.

.. code-block:: python

   from GONet_Wizard.commands.cli_core import CommandSpec

   COMMAND = CommandSpec(
       name="my_command",
       help="Short description shown in CLI help.",
       args=[
           {
               "flags": ["input"],
               "help": "Input path.",
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

Register the command in ``GONet_Wizard/commands/__init__.py`` by adding the
module to ``COMMANDS``.

.. code-block:: python

   COMMANDS = (
       show,
       show_meta,
       extract,
       run_dashboard,
       build_full_array,
       gui,
       my_command,
   )

After registration, ``parser_builder.build_subparser()`` discovers the command
through the root ``PARSER`` and adds it to the ``argparse`` command tree.

Relevant files and objects:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File
     - Objects or functions
   * - ``GONet_Wizard/commands/specs.py``
     - ``CommandSpec``, ``ParserSpec``
   * - ``GONet_Wizard/commands/__init__.py``
     - ``COMMANDS``, root ``PARSER``
   * - ``GONet_Wizard/commands/parser_builder.py``
     - ``build_subparser()``, ``register_simple_subcommand()``
   * - ``GONet_Wizard/cli.py``
     - ``main()``

Adding Command Arguments
------------------------

Command arguments are declared as dictionaries inside ``COMMAND.args``.

The dictionaries are passed to ``argparse.ArgumentParser.add_argument()``.

Positional argument example:

.. code-block:: python

   {
       "flags": ["filenames"],
       "nargs": "+",
       "action": ExpandFilenames,
       "help": "Input GONet files.",
   }

Optional flag example:

.. code-block:: python

   {
       "flags": ["--output"],
       "help": "Output filename.",
   }

Boolean flag example:

.. code-block:: python

   {
       "flags": ["--debug"],
       "action": "store_true",
       "default": False,
       "help": "Enable debug mode.",
   }

When possible, reuse shared helpers such as
``GONet_Wizard.commands.inputs.ExpandFilenames`` and
``GONet_Wizard.commands.inputs.filter_by_ext()`` so path behavior remains
consistent across commands.

Adding a GUI Form for a Command
-------------------------------

GUI forms are thin frontends over the command system.

The form should collect values that correspond to the command's argparse
destination names. When the form is submitted, ``GONet_Wizard/gui/web.py``
converts the payload to an ``argv`` list through
``payload_to_argv_with_parser()``.

The form submission path is:

.. code-block:: text

   HTML form
        |
        v

   POST /run
        |
        v

   gui.web.run_command()
        |
        v

   payload_to_argv_with_parser()
        |
        v

   parser.parse_args(argv)
        |
        v

   args.handler(args)

A command-specific form normally lives under the GUI templates directory as a
``forms/<command>.html`` template. The launcher route
``/cmd/<cmd>`` renders that form through ``form_page.html``.

Relevant files and functions:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File
     - Objects or functions
   * - ``GONet_Wizard/gui/web.py``
     - ``command_page()``, ``run_command()``, ``payload_to_argv_with_parser()``
   * - ``GONet_Wizard/commands/parser_builder.py``
     - ``register_simple_subcommand()``
   * - ``GONet_Wizard/commands/ui_bridge.py``
     - ``wrap_handler_for_ui()``
   * - ``GONet_Wizard/ui/server.py``
     - ``create_app()``, ``ensure_server_running()``

Adding a Preview-Producing Command
----------------------------------

Some commands produce HTML previews rather than only terminal output.

The simplest preview-compatible return value is an HTML string.

When a wrapped handler returns a string, ``commands/ui_bridge.py`` treats it as
legacy preview HTML. It publishes the HTML under the command name and opens the
corresponding ``/view/<command>`` preview window.

For more explicit control, return ``PublishRequest`` or ``WindowRequest``.

.. code-block:: python

   from GONet_Wizard.commands.ui_bridge import PublishRequest, WindowRequest
   from GONet_Wizard.ui.windows import WindowSpec

   return WindowRequest(
       key="my-preview",
       publish=PublishRequest(
           channel="my-preview",
           html=html,
           title="My Preview",
       ),
       spec=WindowSpec(
           title="My Preview",
           url=f"http://127.0.0.1:{port}/view/my-preview",
           width=1200,
           height=800,
       ),
   )

Use stable window keys so repeated command runs reuse or refresh existing
windows instead of creating unrelated duplicates.

Adding a Dash-Based Tool
------------------------

Dash-based tools should use the shared Dash runner rather than starting Dash
servers manually.

The standard pattern is:

#. Define or import the Dash app.
#. Create a ``DashLaunchSpec``.
#. Configure runtime inputs through a configuration function.
#. Register callbacks through a callback-registration function.
#. Start or reuse the app with ``ensure_dash_running()``.
#. Return a ``WindowRequest`` pointing to the Dash URL.

Conceptually:

.. code-block:: python

   from GONet_Wizard.ui.dash_runner import DashLaunchSpec, ensure_dash_running

   spec = DashLaunchSpec(
       app=app,
       app_key="my-dash-tool",
       configure=configure_app,
       layout=build_layout,
       register_callbacks=register_callbacks,
   )

   url = ensure_dash_running(spec, debug=debug, port=port)

The dashboard and the interactive extraction GUI both follow this model.

Relevant files:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File
     - Role
   * - ``GONet_Wizard/ui/dash_runner.py``
     - Shared Dash server lifecycle.
   * - ``GONet_Wizard/commands/run_dashboard.py``
     - Dashboard command launch path.
   * - ``GONet_Wizard/GONet_utils/src/extract_app/extract_gui.py``
     - Interactive extraction GUI launch path.
   * - ``GONet_Wizard/ui/windows.py``
     - Managed PyWebview windows.

Adding a New Extractor
----------------------

Extraction outputs are assembled from independent extractor components.

A new extractor should subclass ``Extractor`` from
``GONet_Wizard/GONet_utils/src/extractors/core.py``.

A minimal extractor declares:

* ``USES``: context keys it requires,
* ``PROVIDES``: context keys it adds,
* ``extract(raw, context)``: the method that returns results and updated
  context.

.. code-block:: python

   from GONet_Wizard.GONet_utils.src.extractors.core import Extractor

   class MyExtractor(Extractor):

       USES = ["time"]
       PROVIDES = ["my_context_value"]

       def extract(self, raw, context):
           results = {
               "my_output_field": "...",
           }

           context["my_context_value"] = "..."

           return results, context

To include the extractor in the standard extraction workflow, add it to
``ALL_EXTRACTORS`` in ``GONet_Wizard/GONet_utils/src/extractors/runner.py``.

The execution order is determined by ``sort_extractors()`` from
``extractors/core.py``, based on declared ``USES`` and ``PROVIDES`` values.

Relevant files and objects:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - File
     - Objects or functions
   * - ``extractors/core.py``
     - ``Extractor``, ``sort_extractors()``, ``extraction_output``
   * - ``extractors/runner.py``
     - ``ALL_EXTRACTORS``, ``extract_all()``
   * - ``extractors/merge.py``
     - ``merge_extractor_into_data()``
   * - ``extractors/extraction_values.py``
     - Pixel-statistics extractor and region-mask workflow.

Adding User Documentation
-------------------------

When adding a new feature, update documentation at the correct layer.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Documentation area
     - Use it for
   * - ``tools/``
     - What the feature does and when users should use it.
   * - ``gui_guide/``
     - How to use the feature from the graphical interface.
   * - ``cli_reference/``
     - Exact terminal syntax and examples.
   * - ``developer_notes/``
     - Architecture, implementation details, and contributor guidance.
   * - ``api_reference/``
     - Generated module, class, and function reference.

For example, adding a new GUI-accessible command may require:

* a Tools page,
* a GUI Guide page,
* a CLI Reference page,
* a Developer Notes section,
* API Reference coverage.

Checklist: New Command
----------------------

Before considering a new command complete, check that:

* The command defines ``COMMAND``.
* The command defines ``cli_handler(args)``.
* The command is registered in ``commands/__init__.py``.
* Inputs use shared expansion/filtering helpers where appropriate.
* The command works from the terminal.
* GUI behavior, if any, returns UI result objects rather than creating windows
  directly.
* Tests cover parser construction and representative handler behavior.
* Documentation links the feature across Tools, GUI, CLI, Developer Notes, and
  API Reference as needed.

Checklist: New GUI Window
-------------------------

Before adding a new GUI window, check that:

* The window is represented by a stable key.
* Window creation goes through ``WindowRequest`` or ``WINDOWS.ensure()``.
* The PyWebview event loop is not started directly from feature code.
* The unified Flask server or Dash runner owns the web server lifecycle.
* Repeated launches reuse or refresh the existing window when appropriate.

Checklist: New Extractor
------------------------

Before adding a new extractor, check that:

* ``USES`` includes every required context key.
* ``PROVIDES`` includes every new context key.
* ``PROVIDES`` does not collide with another extractor unless that is
  intentional.
* The extractor returns an output dictionary and updated context.
* The extractor is added to ``ALL_EXTRACTORS`` only if it belongs in the
  standard workflow.
* Tests cover dependency ordering and output merging.

Summary
-------

Most GONet Wizard extensions follow one of three patterns:

* add a command,
* add a GUI or Dash presentation for a command,
* add an extraction component.

The command system, GUI architecture, UI runtime, and extractor framework are
designed to keep those changes modular. Contributors should prefer the existing
extension points over direct coupling between subsystems.
