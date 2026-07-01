``show_meta``
=============

The ``show_meta`` command displays metadata from one or more GONet image files.

By default, metadata is printed as terminal text. The command can also generate
HTML output for GUI-backed preview workflows. In the graphical preview, the
metadata window includes **Save PDF** and **Exit** actions; **Save PDF** writes
the displayed metadata tables to a PDF file.

For the conceptual tool guide, see :doc:`metadata inspection tool guide <../tools/inspect_metadata>`.

Usage
-----

.. code-block:: bash

   GONet_Wizard show_meta [-h] [--html] filenames [filenames ...]

Arguments
---------

``filenames``
   One or more GONet image files to inspect.

   The command supports files, folders, wildcards, and comma-separated lists.

Options
-------

``--html``
   Return metadata as HTML instead of plain terminal text.

   This option is mainly useful for GUI and preview-backed workflows. When the
   HTML preview is opened through the desktop UI, the preview includes a
   **Save PDF** button that writes the displayed metadata tables to disk.

Examples
--------

Print metadata for one image:

.. code-block:: bash

   GONet_Wizard show_meta image.jpg

Print metadata for several images:

.. code-block:: bash

   GONet_Wizard show_meta image1.jpg image2.jpg

Inspect metadata using a wildcard:

.. code-block:: bash

   GONet_Wizard show_meta *.jpg

Generate HTML metadata output:

.. code-block:: bash

   GONet_Wizard show_meta image.jpg --html

GUI Equivalent
--------------

The graphical equivalent is :doc:`Show Metadata GUI guide <../gui_guide/show_meta>`.

Related Pages
-------------

* :doc:`metadata inspection tool guide <../tools/inspect_metadata>`
* :doc:`GONet images user guide <../user_guide/gonet_images>`
* :doc:`GONetFile user guide <../user_guide/gonetfile>`
* :doc:`common CLI patterns <common_patterns>`
