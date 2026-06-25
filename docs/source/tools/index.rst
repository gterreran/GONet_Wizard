Tools
=====

This section describes the main user-facing tools provided by GONet Wizard.

These pages focus on *what each tool does* and *when to use it*. Concrete GUI
instructions live in the :doc:`GUI Guide <../gui_guide/index>`, while terminal commands are
documented in the :doc:`CLI Reference <../cli_reference/index>`.

Tool Overview
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 40 20 15

   * - Tool
     - Purpose
     - GUI page
     - CLI page
   * - :doc:`image inspection tool guide <inspect_images>`
     - Visualize GONet images, compare observations, and inspect Bayer channels.
     - :doc:`Show Image GUI guide <../gui_guide/show>`
     - :doc:`show CLI reference <../cli_reference/show>`
   * - :doc:`metadata inspection tool guide <inspect_metadata>`
     - Review acquisition metadata, camera settings, timestamps, and image geometry.
     - :doc:`Show Metadata GUI guide <../gui_guide/show_meta>`
     - :doc:`show_meta CLI reference <../cli_reference/show_meta>`
   * - :doc:`extraction tool guide <extract_measurements>`
     - Measure counts in user-defined image regions and save JSON/CSV products.
     - :doc:`Extract GUI guide <../gui_guide/extract>`
     - :doc:`extract CLI reference <../cli_reference/extract>`
   * - :doc:`dashboard tool guide <dashboard>`
     - Explore extracted JSON/CSV products in an interactive dashboard.
     - :doc:`Dashboard GUI guide <../gui_guide/dashboard>`
     - :doc:`dashboard CLI reference <../cli_reference/dashboard>`

.. toctree::
   :maxdepth: 2

   inspect_images
   inspect_metadata
   extract_measurements
   dashboard

Tool Names and Command Names
----------------------------

The same functionality is described from several perspectives throughout the
manual. The table below maps the user-facing tool name to the GUI page and CLI
command name.

.. list-table::
   :header-rows: 1
   :widths: 30 25 25 20

   * - Tool page
     - GUI label
     - CLI command
     - Developer notes
   * - :doc:`image inspection tool guide <inspect_images>`
     - Show Image
     - ``show``
     - :doc:`GUI architecture developer notes <../developer_notes/gui_architecture>`
   * - :doc:`metadata inspection tool guide <inspect_metadata>`
     - Show Metadata
     - ``show_meta``
     - :doc:`GUI architecture developer notes <../developer_notes/gui_architecture>`
   * - :doc:`extraction tool guide <extract_measurements>`
     - Extract
     - ``extract``
     - :doc:`extractor architecture developer notes <../developer_notes/extractor_architecture>`
   * - :doc:`dashboard tool guide <dashboard>`
     - Dashboard
     - ``dashboard``
     - :doc:`UI runtime developer notes <../developer_notes/ui_runtime>`

How These Pages Relate
----------------------

The Tools pages are intentionally interface-neutral. They explain the purpose,
inputs, outputs, and typical use cases of each tool.

For step-by-step interface instructions, use the GUI Guide or CLI Reference.
For implementation details, use the Developer Notes and API Reference.

See also:

* :doc:`User Guide <../user_guide/index>`
* :doc:`GUI Guide <../gui_guide/index>`
* :doc:`CLI Reference <../cli_reference/index>`
* :doc:`Developer Notes <../developer_notes/index>`
