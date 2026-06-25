.. _user-guide-gui-vs-cli:

GUI and CLI
===========

GONet Wizard provides both a graphical interface and a command-line interface.
They are different entry points into the same package, not separate
implementations.

A useful way to think about the architecture is:

.. code-block:: text

   GUI forms and windows
            \
             -> shared command and processing engine
            /
   command-line interface

This means that the GUI is not a simplified fork of the code and the CLI is not
a separate backend. Both interfaces call into the same command definitions,
loaders, file models, extraction utilities, plotting logic, and output writers.

Installation paths
------------------

The GUI and CLI share code, but they can be installed through different user
paths. This distinction is important.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Installation path
     - What the user launches
     - CLI availability
   * - Desktop installer or DMG
     - A double-click ``GONet Wizard`` app.
     - Does not install ``GONet_Wizard`` or ``gonet-wizard`` shell commands.
   * - Python package installation
     - Terminal commands such as ``GONet_Wizard show`` and
       ``GONet_Wizard gui``.
     - Installs the public CLI entry points, assuming the Python script
       directory is on ``PATH``.

Use the desktop installer when you want to avoid the terminal entirely. Use the
Python package installation when you want command-line tools, scripting, or a
development environment. See :doc:`../installation` for installation details.

When to use the GUI
-------------------

The graphical interface is useful when you want to:

- explore files interactively;
- fill command options through forms instead of remembering syntax;
- preview plots or extraction regions;
- use task-specific windows such as the extraction GUI;
- run occasional workflows without scripting.

The GUI is especially helpful when you are learning the package or working with
one file at a time.

When to use the CLI
-------------------

The command-line interface is useful when you want to:

- automate repeated workflows;
- process many files;
- run commands from scripts;
- integrate GONet Wizard into a larger analysis pipeline;
- reproduce the same operation exactly.

The CLI is usually the best choice for batch processing and scripted analysis.

Same inputs, same results
-------------------------

Because the GUI and CLI share the same processing engine, equivalent operations
should produce equivalent results. The difference is how the user supplies
options and views feedback:

- the CLI receives arguments directly from the shell;
- the GUI collects options through forms and interactive controls;
- both convert those choices into the same internal command execution path.

This relationship is important for reproducibility. A workflow discovered
through the GUI can often be translated into a CLI command later, and a CLI
workflow can often be exposed through the graphical launcher for easier use.

Where to Go Next
----------------

* :doc:`GUI Guide <../gui_guide/index>`
* :doc:`CLI Reference <../cli_reference/index>`
* :doc:`command-system developer notes <../developer_notes/command_system>`

