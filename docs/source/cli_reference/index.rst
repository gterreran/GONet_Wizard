CLI Reference
=============

This section documents the public GONet Wizard command-line interface.

The CLI is useful for:

* Inspecting images and metadata from the terminal.
* Running repeatable extractions.
* Launching GUI-backed tools from scripts or shell commands.
* Processing groups of files with folders, wildcards, or comma-separated lists.

For a conceptual overview of the available tools, see :doc:`Tools guide <../tools/index>`.

For implementation details about how commands are declared and dispatched, see
:doc:`command-system developer notes <../developer_notes/command_system>`.

.. important::

   The desktop installer/DMG is a GUI-first distribution path and does not add
   command-line entry points to your shell. To use this CLI reference, install
   the Python package with ``pip`` or ``pipx`` so that ``GONet_Wizard`` and
   ``gonet-wizard`` are available from the terminal.

Basic Usage
-----------

The general command structure is:

.. code-block:: bash

   GONet_Wizard [global-options] <command> [command-options]

To show the top-level help page:

.. code-block:: bash

   GONet_Wizard --help

To show help for a specific command:

.. code-block:: bash

   GONet_Wizard show --help
   GONet_Wizard extract --help

Available Commands
------------------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Command
     - Purpose
     - GUI equivalent
   * - ``show``
     - Inspect one or more GONet images by Bayer channel.
     - :doc:`Show Image GUI guide <../gui_guide/show>`
   * - ``show_meta``
     - Print or render metadata for one or more GONet images.
     - :doc:`Show Metadata GUI guide <../gui_guide/show_meta>`
   * - ``extract``
     - Extract pixel-count measurements from selected image regions.
     - :doc:`Extract GUI guide <../gui_guide/extract>`
   * - ``dashboard``
     - Launch the interactive dashboard from JSON or CSV data products.
     - :doc:`Dashboard GUI guide <../gui_guide/dashboard>`
   * - ``build_full_array``
     - Build full-array GONet products by combining Bayer channels.
     - Command-line only
   * - ``gui``
     - Launch the graphical GONet Wizard launcher.
     - :doc:`GUI launcher guide <../gui_guide/launcher>`

Global Options
--------------

The top-level command supports several global options.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``-h``, ``--help``
     - Show help text.
   * - ``--version``
     - Print the installed GONet Wizard version.
   * - ``--ui-port UI_PORT``
     - Port for the unified local UI server used by preview and GUI pages.
   * - ``--debug-webview``
     - Enable PyWebview debug mode.
   * - ``--log-level LEVEL``
     - Enable package logging at one of ``DEBUG``, ``INFO``, ``WARNING``,
       ``ERROR``, or ``CRITICAL``.

.. note::

   Global options are placed before the command name.

   For example:

   .. code-block:: bash

      GONet_Wizard --log-level INFO show image.jpg

Command Pages
-------------

.. toctree::
   :maxdepth: 2

   common_patterns
   show
   show_meta
   extract
   dashboard
   build_full_array
   gui


CLI Command Names and Tool Pages
--------------------------------

Most commands correspond directly to a user-facing tool page.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Command
     - Tool page
     - Notes
   * - ``show``
     - :doc:`image inspection tool guide <../tools/inspect_images>`
     - Opens image inspection previews.
   * - ``show_meta``
     - :doc:`metadata inspection tool guide <../tools/inspect_metadata>`
     - Prints text output or returns HTML for GUI previews.
   * - ``extract``
     - :doc:`extraction tool guide <../tools/extract_measurements>`
     - Runs direct extraction or launches the interactive extraction app.
   * - ``dashboard``
     - :doc:`dashboard tool guide <../tools/dashboard>`
     - Launches a Dash application from JSON/CSV products.
   * - ``build_full_array``
     - No general user-facing tool page yet.
     - Advanced command-line-only workflow.
   * - ``gui``
     - :doc:`GUI launcher guide <../gui_guide/launcher>`
     - Opens the graphical launcher.

How the CLI Relates to Other Docs
---------------------------------

The CLI Reference is intentionally practical: it shows command syntax, options,
and examples.

For conceptual tool descriptions, see :doc:`Tools guide <../tools/index>`. For GUI usage, see
:doc:`GUI Guide <../gui_guide/index>`. For command-system internals, see
:doc:`command-system developer notes <../developer_notes/command_system>`.
