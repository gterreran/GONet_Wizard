``build_full_array``
====================

The ``build_full_array`` command builds full-array GONet image products by
histogram matching and combining Bayer channels.


Intended Audience
-----------------

``build_full_array`` is a more specialized command than the main user-facing
tools.

It is intentionally less prominent than commands such as ``show``,
``show_meta``, ``extract``, and ``dashboard`` because it is mainly intended for
users who already understand the lower-level GONet data format and the role of
Bayer-channel reconstruction in the processing workflow.

Most users will not need to run this command directly during routine image
inspection or extraction workflows.

There is currently no graphical interface for ``build_full_array``. It is
available only through the command line.


Usage
-----

.. code-block:: bash

   GONet_Wizard build_full_array [-h] [--show] [--outfile OUTFILE]
                                 [--verbose] [--weights WEIGHTS]
                                 input [input ...]

Arguments
---------

``input``
   One or more input GONet RAW ``.jpg`` files.

   If a folder is provided, all ``.jpg`` files in that folder are used.

Options
-------

``--show``
   Show diagnostic plots, including histograms, KDEs, and the combined image.

``--outfile OUTFILE``
   Output filename.

   If omitted, the default is based on the input basename and ends with
   ``_full_array.npz``.

``--verbose``
   Enable verbose logging at ``INFO`` level.

``--weights WEIGHTS``
   Optional channel weights as comma-separated ``name=value`` pairs.

   Example:

   .. code-block:: text

      red=0.25,green1=0.5,green2=0.5,blue=0.25

   Missing channels default to ``1.0``. Extra names are ignored.

Examples
--------

Build a full-array product from one file:

.. code-block:: bash

   GONet_Wizard build_full_array image.jpg

Build from all ``.jpg`` files in a folder:

.. code-block:: bash

   GONet_Wizard build_full_array /path/to/images

Specify an output file:

.. code-block:: bash

   GONet_Wizard build_full_array image.jpg --outfile image_full_array.npz

Show diagnostic plots:

.. code-block:: bash

   GONet_Wizard build_full_array image.jpg --show

Use custom channel weights:

.. code-block:: bash

   GONet_Wizard build_full_array image.jpg --weights "red=0.25,green1=0.5,green2=0.5,blue=0.25"

GUI Equivalent
--------------

There is currently no GUI access for this command.

This is intentional: ``build_full_array`` is a specialized command for advanced
workflows and is less oriented toward average GUI users than the main
inspection, metadata, extraction, and dashboard tools.

Related Pages
-------------

* :doc:`common CLI patterns <common_patterns>`
* :doc:`commands API reference <../api_reference/commands>`
