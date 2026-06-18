Dashboard Architecture
======================

The dashboard is a relatively self-contained Dash application used for quick
inspection of extraction products.

Compared with the command system, GUI form layer, UI runtime, and extractor
framework, the dashboard has a simpler architecture: it loads extraction JSON
or CSV products, discovers the available fields, exposes them through plotting
and filtering controls, and lets users export filtered subsets for later
analysis.

This page documents the dashboard at a high level so contributors know where it
fits in the larger GONet Wizard architecture.

See also:

* :doc:`dashboard tool guide <../tools/dashboard>`
* :doc:`Dashboard GUI guide <../gui_guide/dashboard>`
* :doc:`dashboard CLI reference <../cli_reference/dashboard>`
* :doc:`UI runtime developer notes <ui_runtime>`

Role in the Project
-------------------

The dashboard is best understood as a quick-look data exploration layer.

It is not responsible for:

* extracting counts from images,
* defining extraction regions,
* interpreting observations scientifically,
* performing advanced statistical analysis.

Those tasks belong to other layers or to downstream analysis scripts.

The dashboard is responsible for:

* loading tabular products produced by extraction workflows,
* exposing available quantities to the user,
* plotting selected quantities,
* applying simple interactive filters,
* preserving or restoring filter state,
* exporting the currently selected subset.

Launch Path
-----------

The dashboard can be launched from either the CLI or the GUI.

The command-line path starts in ``GONet_Wizard/commands/run_dashboard.py``.

At a high level, that command:

#. Expands input paths.
#. Filters inputs to supported data products.
#. Resolves the optional image-preview path.
#. Starts or reuses the Dash dashboard server.
#. Returns a ``WindowRequest`` for the managed dashboard window.

The GUI launcher path reaches the same command through the form system described
in :doc:`GUI architecture developer notes <gui_architecture>`.

Conceptually:

.. code-block:: text

   Dashboard GUI form or `GONet_Wizard dashboard`
        |
        v

   commands/run_dashboard.py
        |
        v

   ensure_dashboard_running(...)
        |
        v

   Dash server
        |
        v

   WindowRequest("dashboard")
        |
        v

   managed PyWebview window

The window and server lifecycle is handled by the shared UI runtime. The
dashboard command should not create PyWebview windows directly.

Data Model
----------

The dashboard is intentionally driven by the contents of the loaded data
products.

Instead of hardcoding a fixed set of columns, the dashboard reads the available
fields from the input JSON or CSV files and uses them to populate controls such
as:

* the X-axis dropdown,
* the Y-axis dropdown,
* filter quantity dropdowns.

This design keeps the dashboard compatible with future extraction products. If
new extractors add new output fields, those fields can become available to the
dashboard without requiring a manually maintained list of column names.

Channel-Dependent Quantities
----------------------------

Some extraction fields are channel dependent.

For example, extraction outputs may contain values such as red, green, or blue
``mean_counts``.

The dashboard represents these as plottable quantities with optional channel
selection. When the selected quantity depends on channel, the channel checkboxes
control which channel-specific series are displayed.

Filtering Model
---------------

The dashboard filter system is designed for simple exploratory cuts.

A filter combines:

* a quantity name,
* a comparison operator,
* a numeric threshold,
* an enabled or disabled state.

Some filter rows may include an additional OR condition. This allows common
selection patterns such as keeping observations that satisfy one of two
related criteria.

Filtered-out points may either remain visible with reduced opacity or disappear
from the graph, depending on the **Show filtered data** toggle.

Export Model
------------

The dashboard export operation writes the current filtered subset.

The export is intentionally data-preserving: exported observations should
include all available quantities stored for those observations, not only the
currently plotted X and Y quantities.

This makes the dashboard useful as a selection tool. Users can interactively
identify a subset and then continue analysis in scripts, notebooks, or other
software.

State Persistence
-----------------

The dashboard includes save/load controls for dashboard state.

This allows users to preserve useful filter configurations and restore them in
later sessions.

From an architecture perspective, this state is dashboard-specific UI state. It
should remain separate from the extraction products themselves.

Relationship to the UI Runtime
------------------------------

The dashboard is hosted as a Dash app, but displayed through the same desktop
runtime used by the rest of the GUI.

The important runtime responsibilities are:

* starting or reusing the Dash server,
* opening or focusing the dashboard window,
* keeping dashboard window management consistent with other GUI windows.

For details about Dash server management and PyWebview windows, see
:doc:`UI runtime developer notes <ui_runtime>`.

Contributor Notes
-----------------

Dashboard changes usually fall into one of a few categories.

Data loading changes
   Affect how JSON or CSV products are read and normalized.

Control-generation changes
   Affect which fields appear in dropdowns or filter controls.

Plotting changes
   Affect how selected quantities are rendered.

Filtering changes
   Affect how filter rows are evaluated and how filtered-out points are shown.

Export changes
   Affect which observations and fields are written to the exported subset.

When modifying the dashboard, keep the dynamic-field behavior in mind. Avoid
hardcoding extractor-specific field names unless there is a clear reason to do
so.

Summary
-------

The dashboard is intentionally simpler and more standalone than the rest of the
GUI architecture.

Its main responsibility is to provide an interactive quick-look view of
extraction products. It should remain flexible enough to follow the extraction
output schema as new extractors add new fields, while leaving advanced analysis
to downstream user workflows.
