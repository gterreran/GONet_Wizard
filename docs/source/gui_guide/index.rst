GUI Guide
=========

The GUI Guide explains how to use the graphical GONet Wizard interface.

These pages focus on *what the user sees on screen*: which fields to fill,
which buttons to press, and what happens after each form is submitted.

For conceptual descriptions of the tools themselves, see :doc:`Tools guide <../tools/index>`.
For terminal usage, see :doc:`CLI Reference <../cli_reference/index>`. For implementation
details, see :doc:`GUI architecture developer notes <../developer_notes/gui_architecture>` and
:doc:`UI runtime developer notes <../developer_notes/ui_runtime>`.

.. note::

   The downloadable desktop app is intended for GUI use. It opens the graphical
   launcher without requiring a terminal, but it does not install the
   ``GONet_Wizard`` or ``gonet-wizard`` command-line tools. Install the Python
   package if you also want terminal commands.

GUI Pages
---------

.. list-table::
   :header-rows: 1
   :widths: 25 45 30

   * - Page
     - Purpose
     - Related tool
   * - :doc:`GUI launcher guide <launcher>`
     - Open the main GUI launcher and choose a tool.
     - :doc:`Tools guide <../tools/index>`
   * - :doc:`Show Image GUI guide <show>`
     - Launch image inspection from the GUI.
     - :doc:`image inspection tool guide <../tools/inspect_images>`
   * - :doc:`Show Metadata GUI guide <show_meta>`
     - Launch metadata inspection from the GUI.
     - :doc:`metadata inspection tool guide <../tools/inspect_metadata>`
   * - :doc:`Extract GUI guide <extract>`
     - Launch direct or interactive extraction from the GUI.
     - :doc:`extraction tool guide <../tools/extract_measurements>`
   * - :doc:`Split RAW Images GUI guide <split_raw>`
     - Convert RAW GONet ``.jpg`` files into standard TIFF/JPEG products.
     - :doc:`split RAW images tool guide <../tools/split_raw_images>`
   * - :doc:`Dashboard GUI guide <dashboard>`
     - Launch the dashboard from a data directory.
     - :doc:`dashboard tool guide <../tools/dashboard>`

.. toctree::
   :maxdepth: 2

   launcher
   show
   show_meta
   extract
   split_raw
   dashboard

GUI Labels and CLI Commands
---------------------------

Each GUI page is a form-based frontend over a command-line command.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - GUI page
     - CLI command
     - Tool description
   * - :doc:`Show Image GUI guide <show>`
     - ``show``
     - :doc:`image inspection tool guide <../tools/inspect_images>`
   * - :doc:`Show Metadata GUI guide <show_meta>`
     - ``show_meta``
     - :doc:`metadata inspection tool guide <../tools/inspect_metadata>`
   * - :doc:`Extract GUI guide <extract>`
     - ``extract``
     - :doc:`extraction tool guide <../tools/extract_measurements>`
   * - :doc:`Split RAW Images GUI guide <split_raw>`
     - ``split_raw``
     - :doc:`split RAW images tool guide <../tools/split_raw_images>`
   * - :doc:`Dashboard GUI guide <dashboard>`
     - ``dashboard``
     - :doc:`dashboard tool guide <../tools/dashboard>`

Relationship to the CLI
-----------------------

The graphical interface is a frontend over the same command system used by the
terminal CLI. The GUI forms collect inputs, translate them into command
arguments, and dispatch the same handlers used by command-line invocations.

For the equivalent terminal commands, see :doc:`CLI Reference <../cli_reference/index>`.
For the internal architecture, see :doc:`command-system developer notes <../developer_notes/command_system>`.
