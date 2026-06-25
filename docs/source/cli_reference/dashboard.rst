``dashboard``
=============

The ``dashboard`` command launches the interactive GONet Wizard dashboard from
JSON or CSV data products.

The dashboard is a GUI-backed Dash application that opens in a managed desktop
window.

Usage
-----

.. code-block:: bash

   GONet_Wizard dashboard [-h] [--debug] [--port PORT] input [input ...]

Arguments
---------

``input``
   One or more input data paths.

   Inputs may be JSON files, CSV files, or directories containing supported data
   products.

Options
-------

``--debug``
   Run the dashboard in debug mode with more verbose logging.

``--port PORT``
   Port for the Dash server.

Examples
--------

Launch the dashboard from a directory of extraction outputs:

.. code-block:: bash

   GONet_Wizard dashboard results/

Launch the dashboard from specific files:

.. code-block:: bash

   GONet_Wizard dashboard extraction_1.json extraction_2.json

Launch the dashboard on a custom port:

.. code-block:: bash

   GONet_Wizard dashboard results/ --port 8050

GUI Equivalent
--------------

The graphical equivalent is :doc:`Dashboard GUI guide <../gui_guide/dashboard>`.

Related Pages
-------------

* :doc:`dashboard tool guide <../tools/dashboard>`
* :doc:`extraction tool guide <../tools/extract_measurements>`
* :doc:`UI runtime developer notes <../developer_notes/ui_runtime>`
* :doc:`common CLI patterns <common_patterns>`
