``show``
========

The ``show`` command opens one or more GONet images in the image inspection
viewer.

It can display selected Bayer channels. Export is available from inside the
interactive viewer with the **Save figure** button.

For the conceptual tool guide, see :doc:`image inspection tool guide <../tools/inspect_images>`.

Usage
-----

.. code-block:: bash

   GONet_Wizard show [-h] [--blue] [--green] [--red] filenames [filenames ...]

Arguments
---------

``filenames``
   One or more GONet image files to inspect.

   The command supports files, folders, wildcards, and comma-separated lists.

Options
-------

``--blue``
   Display the blue channel.

``--green``
   Display the green channel.

``--red``
   Display the red channel.

If no channel flags are provided, all channels are displayed.

Examples
--------

Inspect one image:

.. code-block:: bash

   GONet_Wizard show image.jpg

Inspect several images:

.. code-block:: bash

   GONet_Wizard show image1.jpg image2.jpg image3.jpg

Inspect files using a wildcard:

.. code-block:: bash

   GONet_Wizard show *.jpg

Inspect only the red channel:

.. code-block:: bash

   GONet_Wizard show image.jpg --red

Inspect blue and green channels:

.. code-block:: bash

   GONet_Wizard show image.jpg --blue --green

Save the visualization:

   Open the viewer, adjust the figure if needed, then click **Save figure**.
   GONet Wizard opens the operating-system save dialog and writes the export
   after the viewer window closes. Supported extensions are ``.pdf``, ``.png``,
   ``.jpg``, ``.jpeg``, ``.webp``, ``.svg``, ``.html``, and ``.htm``. If no
   extension is provided, ``.pdf`` is appended automatically. Static image
   formats use Plotly/Kaleido. With Kaleido v1, Chrome or Chromium must be
   available on the machine running the command. ``.html`` export avoids Kaleido.

GUI Equivalent
--------------

The graphical equivalent is :doc:`Show Image GUI guide <../gui_guide/show>`.

Related Pages
-------------

* :doc:`image inspection tool guide <../tools/inspect_images>`
* :doc:`channels user guide <../user_guide/channels>`
* :doc:`common CLI patterns <common_patterns>`
