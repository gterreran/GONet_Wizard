Developer Notes
===============

The Developer Notes describe the internal architecture of GONet Wizard.

Unlike the :doc:`User Guide <../user_guide/index>`, which focuses on concepts and usage,
these pages explain how the package is implemented and how the major systems
interact.

These notes are intended for contributors, advanced users, and future maintainers.

Architecture Map
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Page
     - Focus
   * - :doc:`command-system developer notes <command_system>`
     - How commands are declared, registered, parsed, dispatched, and shared by CLI and GUI workflows.
   * - :doc:`GUI architecture developer notes <gui_architecture>`
     - How GUI forms connect to the command system and how GUI commands request presentation.
   * - :doc:`UI runtime developer notes <ui_runtime>`
     - How Flask, PyWebview, preview windows, Dash apps, and runtime window management fit together.
   * - :doc:`extractor architecture developer notes <extractor_architecture>`
     - How extraction outputs are composed from independent extractor components.
   * - :doc:`dashboard architecture developer notes <dashboard_architecture>`
     - How the dashboard loads extraction products, discovers fields, filters data, and exports subsets.
   * - :doc:`contributor workflows developer notes <contributor_workflows>`
     - Practical recipes for adding commands, GUI forms, Dash tools, and extractors.
   * - :doc:`desktop packaging developer notes <packaging>`
     - How the desktop entry point, resource paths, PyInstaller specs, and macOS DMG wrapper fit together.
   * - :doc:`release workflow developer notes <release_workflow>`
     - How to build, test, and publish large installer artifacts without committing them to git.

.. toctree::
   :maxdepth: 2

   command_system
   gui_architecture
   ui_runtime
   extractor_architecture
   dashboard_architecture
   contributor_workflows
   packaging
   release_workflow

Recommended Reading Order
-------------------------

For contributors, the most useful path is usually:

#. :doc:`command-system developer notes <command_system>` — understand how commands are declared and dispatched.
#. :doc:`GUI architecture developer notes <gui_architecture>` — understand how GUI forms reuse those commands.
#. :doc:`UI runtime developer notes <ui_runtime>` — understand how windows, previews, Flask, PyWebview, and Dash are managed.
#. :doc:`extractor architecture developer notes <extractor_architecture>` — understand how extraction outputs are assembled.
#. :doc:`dashboard architecture developer notes <dashboard_architecture>` — understand the lightweight dashboard data/plot/filter/export flow.
#. :doc:`contributor workflows developer notes <contributor_workflows>` — use the practical recipes when adding features.
#. :doc:`desktop packaging developer notes <packaging>` — review packaging rules when changing resource paths, GUI startup, or build scripts.
#. :doc:`release workflow developer notes <release_workflow>` — review release cadence and artifact handling before publishing installers.

The dashboard is intentionally treated as a more standalone subsystem, but a
lightweight architecture note is included for contributors who need to work on
its data-loading, plotting, filtering, or export behavior.

Code-Level Reference
--------------------

For generated API documentation, see :doc:`API Reference <../api_reference/index>`.
