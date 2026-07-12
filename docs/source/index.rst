============
GONet Wizard
============

GONet Wizard is a command-line and graphical toolkit for working with GONet
camera data. It includes utilities for inspecting GONet images, reading
metadata, extracting measurements from regions of interest, converting RAW
images into standard TIFF/JPEG products, building derived array products, and
launching interactive GUI workflows.

The documentation is organized by reader need. Start with the User Guide for
concepts, the Tools section for task-oriented explanations, the GUI Guide or
CLI Reference for concrete usage, and the Developer Notes or API Reference for
implementation details.

Documentation Layers
--------------------

The documentation is organized so that each section has a distinct role.

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - Section
     - Use it for
     - Typical reader
   * - :doc:`User Guide <user_guide/index>`
     - Core concepts: GONet cameras, GONet images, channels, and file objects.
     - New users
   * - :doc:`Tools guide <tools/index>`
     - Task-oriented descriptions of what each tool does.
     - Users planning an analysis
   * - :doc:`GUI Guide <gui_guide/index>`
     - Step-by-step instructions for each graphical form.
     - GUI users
   * - :doc:`CLI Reference <cli_reference/index>`
     - Terminal syntax, options, and examples.
     - CLI users and automation
   * - :doc:`Developer Notes <developer_notes/index>`
     - Architecture, extension points, and contributor workflows.
     - Contributors
   * - :doc:`API Reference <api_reference/index>`
     - Generated module, class, and function reference.
     - Developers needing code details

Where to Start
--------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - If you want to...
     - Go to...
   * - Learn what GONet Wizard is and how GONet files are structured
     - :doc:`User Guide <user_guide/index>`
   * - Understand what each tool does
     - :doc:`Tools guide <tools/index>`
   * - Use the graphical interface
     - :doc:`GUI Guide <gui_guide/index>`
   * - Run commands from the terminal
     - :doc:`CLI Reference <cli_reference/index>`
   * - Install the package
     - :doc:`installation guide <installation>`
   * - Understand the internal architecture
     - :doc:`Developer Notes <developer_notes/index>`
   * - Look up modules, classes, and functions
     - :doc:`API Reference <api_reference/index>`

User Documentation
------------------

.. toctree::
   :maxdepth: 2
   :caption: User Documentation

   installation
   user_guide/index
   tools/index
   gui_guide/index
   cli_reference/index

Developer and Reference Documentation
-------------------------------------

.. toctree::
   :maxdepth: 2
   :caption: Developer and Reference Documentation

   developer_notes/index
   api_reference/index
   Changelog <https://github.com/gterreran/GONet_Wizard/blob/master/CHANGELOG.md>

Versioning
----------

The package version can be retrieved from the command line:

.. code-block:: bash

   GONet_Wizard --version

or from Python:

.. code-block:: python

   import GONet_Wizard
   print(GONet_Wizard.__version__)
