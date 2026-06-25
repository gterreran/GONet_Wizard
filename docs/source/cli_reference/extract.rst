``extract``
===========

The ``extract`` command measures pixel counts in selected regions of one or more
GONet images.

Extraction can run in two modes:

* **Interactive mode**, which opens the extraction GUI.
* **Direct mode**, which performs extraction immediately from shape parameters
  supplied on the command line.

For the conceptual tool guide, see :doc:`extraction tool guide <../tools/extract_measurements>`.

Usage
-----

.. code-block:: bash

   GONet_Wizard extract [-h] [--blue] [--green] [--red]
                        [--shape {circle,rectangle,annulus,interactive}]
                        [--center CENTER] [--radius RADIUS] [--sides SIDES]
                        [--inner_radius INNER_RADIUS]
                        [--outer_radius OUTER_RADIUS]
                        [--angles ANGLES] [--output OUTPUT]
                        [--output_type {json,csv}] [--debug] [--port PORT]
                        [filenames ...]

Arguments
---------

``filenames``
   One or more GONet image files to extract.

   The command supports files, folders, wildcards, and comma-separated lists.



Launch Behavior
---------------

The ``extract`` command has two different fallback behaviors, depending on how
much information is provided.

Command Form Fallback
~~~~~~~~~~~~~~~~~~~~~

If the command is invoked without the required command-line inputs, GONet Wizard
opens the Extract GUI form.

For example:

.. code-block:: bash

   GONet_Wizard extract

This follows the same command-form fallback described in
:doc:`common CLI patterns <common_patterns>`.

Interactive Extraction Fallback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If input files are provided, but the command is not given enough information to
perform a complete direct extraction, GONet Wizard launches the interactive
extraction app.

For example:

.. code-block:: bash

   GONet_Wizard extract image.jpg

This opens the interactive extraction app because files were provided, but no
direct extraction shape and geometry were specified.

The same applies when the requested workflow is explicitly interactive:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape interactive

Direct extraction only runs immediately when a non-interactive shape is selected
and all parameters required by that shape are provided.


Channel Options
---------------

``--blue``
   Extract the blue channel.

``--green``
   Extract the green channel.

``--red``
   Extract the red channel.

If no channel flags are provided, all channels are extracted.

Shape Options
-------------

``--shape {circle,rectangle,annulus,interactive}``
   Select the extraction shape.

   If the shape is ``interactive`` or no shape is provided, the interactive
   extraction GUI opens.

Circle Extraction
~~~~~~~~~~~~~~~~~

Circular extraction requires:

* ``--shape circle``
* ``--center X,Y``
* ``--radius RADIUS``

Example:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape circle --center 1000,800 --radius 50

Rectangle Extraction
~~~~~~~~~~~~~~~~~~~~

Rectangular extraction requires:

* ``--shape rectangle``
* ``--center X,Y``
* ``--sides WIDTH,HEIGHT``

Example:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape rectangle --center 1000,800 --sides 300,400

Annulus Extraction
~~~~~~~~~~~~~~~~~~

Annular extraction requires:

* ``--shape annulus``
* ``--center X,Y``
* ``--inner_radius INNER_RADIUS``
* ``--outer_radius OUTER_RADIUS``

Example:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape annulus --center 1000,800 --inner_radius 40 --outer_radius 80

Interactive Extraction
~~~~~~~~~~~~~~~~~~~~~~

Interactive extraction opens the dedicated extraction GUI.

Examples:

.. code-block:: bash

   GONet_Wizard extract image.jpg
   GONet_Wizard extract image.jpg --shape interactive

Angle Limits
------------

``--angles ANGLES``
   Optional angular range as ``start_angle,end_angle`` in degrees.

Angles are measured from the positive x axis and increase counter-clockwise.

Example:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape circle --center 1000,800 --radius 100 --angles=-45,45

Output Options
--------------

``--output OUTPUT``
   Output filename.

   If omitted, a default filename based on the extraction shape is generated.

``--output_type {json,csv}``
   Output format.

   JSON is the default output type.

Examples:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape circle --center 1000,800 --radius 50 --output counts.json

   GONet_Wizard extract image.jpg --shape circle --center 1000,800 --radius 50 --output counts.csv --output_type csv

Interactive Runtime Options
---------------------------

``--debug``
   Run the extraction GUI in debug mode.

``--port PORT``
   Port for the extraction GUI Dash server.

These options only matter when the interactive extraction GUI is launched.

Examples
--------

Extract all channels from a circular region:

.. code-block:: bash

   GONet_Wizard extract image.jpg --shape circle --center 1000,800 --radius 50

Extract only the red channel:

.. code-block:: bash

   GONet_Wizard extract image.jpg --red --shape circle --center 1000,800 --radius 50

Extract all matching files to CSV:

.. code-block:: bash

   GONet_Wizard extract *.jpg --shape annulus --center 1000,800 --inner_radius 40 --outer_radius 80 --output annulus_counts.csv --output_type csv

Launch the interactive extraction GUI on a folder:

.. code-block:: bash

   GONet_Wizard extract /path/to/images --shape interactive

GUI Equivalent
--------------

The graphical equivalent is :doc:`Extract GUI guide <../gui_guide/extract>`.

Related Pages
-------------

* :doc:`extraction tool guide <../tools/extract_measurements>`
* :doc:`extractor architecture developer notes <../developer_notes/extractor_architecture>`
* :doc:`channels user guide <../user_guide/channels>`
* :doc:`common CLI patterns <common_patterns>`
