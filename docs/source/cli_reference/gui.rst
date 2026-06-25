``gui``
=======

The ``gui`` command launches the GONet Wizard graphical launcher.

Usage
-----

.. code-block:: bash

   GONet_Wizard gui [-h] [--port PORT]

Options
-------

``--port PORT``
   Port for the unified local UI server.

Examples
--------

Launch the GUI:

.. code-block:: bash

   GONet_Wizard gui

Launch the GUI on a custom port:

.. code-block:: bash

   GONet_Wizard gui --port 5051

Relationship to Other Commands
------------------------------

The GUI launcher provides graphical access to the main GONet Wizard tools:

* Show Image
* Show Metadata
* Extract Region
* Dashboard

These tools use the same command system as the CLI. The GUI collects inputs
through forms and dispatches them through the shared parser and command
handlers.

Related Pages
-------------

* :doc:`GUI launcher guide <../gui_guide/launcher>`
* :doc:`GUI architecture developer notes <../developer_notes/gui_architecture>`
* :doc:`UI runtime developer notes <../developer_notes/ui_runtime>`
* :doc:`command-system developer notes <../developer_notes/command_system>`
