``split_raw``
=============

The ``split_raw`` command converts original GONet RAW ``.jpg`` files into
standard image products that can be opened by ordinary image tools or reused in
later GONet Wizard workflows.

For the conceptual tool guide, see :doc:`split RAW images tool guide <../tools/split_raw_images>`.

Usage
-----

.. code-block:: bash

   GONet_Wizard split_raw [-h] [--outdir OUTDIR]
                          [--format {both,tiff,jpeg}] [--overwrite]
                          [--tiff-white-balance]
                          [--no-jpeg-white-balance]
                          input [input ...]

Arguments
---------

``input``
   One or more original GONet RAW ``.jpg`` files.

   The command supports files, folders, wildcards, and comma-separated lists.
   Inputs are filtered to ``.jpg`` files because this command is meant for the
   original GONet RAW JPEG container, not for already converted ``.jpeg`` or
   ``.tiff`` products.

Output Products
---------------

By default, ``split_raw`` writes both products for each input file:

* ``<stem>.tiff`` — a standard TIFF product.
* ``<stem>.jpeg`` — a standard JPEG product.

The converted JPEG uses the ``.jpeg`` extension intentionally. This avoids
confusing the generated display JPEG with the original RAW ``.jpg`` container
and prevents the default output name from overwriting the source file.

When ``--outdir`` is omitted, products are written next to each input file.
When ``--outdir`` is provided, GONet Wizard creates dedicated product folders:

.. code-block:: text

   OUTDIR/
   ├── tiffs/
   │   └── <stem>.tiff
   └── jpegs/
       └── <stem>.jpeg

The product folders keep TIFF and JPEG outputs separated when converting many
files at once.

Options
-------

``--outdir OUTDIR``
   Optional base output directory.

   If omitted, outputs are written next to each input file. If supplied, TIFF
   outputs are written under ``OUTDIR/tiffs`` and JPEG outputs are written under
   ``OUTDIR/jpegs``. Missing output folders are created automatically.

``--format {both,tiff,jpeg}``
   Select which product type to write.

   The default is ``both``. Use ``tiff`` when only scientific-style TIFF
   products are needed, or ``jpeg`` when only visual products are needed.

``--overwrite``
   Allow existing output files to be replaced.

   Without this flag, the command refuses to overwrite an existing output file.
   This is deliberately conservative because batch conversions can produce many
   files and accidental overwrites are otherwise easy to miss.

``--tiff-white-balance``
   Apply metadata white-balance gains to TIFF outputs.

   TIFF white balance is disabled by default. The default keeps TIFF pixel
   values as faithful as possible to the RAW data, which is usually preferable
   when the TIFF may later be used for scientific extraction or quantitative
   checks.

``--no-jpeg-white-balance``
   Disable metadata white-balance gains for JPEG outputs.

   JPEG white balance is enabled by default because JPEG products are usually
   created for visual inspection, quick review, sharing, or documentation.
   Disable it only when you need the JPEG to reflect the unbalanced channel
   scaling more directly.

Examples
--------

Convert one RAW file to both products next to the input:

.. code-block:: bash

   GONet_Wizard split_raw image.jpg

Convert all RAW files in a folder into a separate output directory:

.. code-block:: bash

   GONet_Wizard split_raw /path/to/raw_images --outdir /path/to/converted

This creates products such as:

.. code-block:: text

   /path/to/converted/tiffs/image.tiff
   /path/to/converted/jpegs/image.jpeg

Write only TIFF products:

.. code-block:: bash

   GONet_Wizard split_raw *.jpg --format tiff --outdir converted

Write only JPEG products:

.. code-block:: bash

   GONet_Wizard split_raw *.jpg --format jpeg --outdir converted

Apply white balance to TIFF products:

.. code-block:: bash

   GONet_Wizard split_raw image.jpg --format tiff --tiff-white-balance

Write JPEG products without white balance:

.. code-block:: bash

   GONet_Wizard split_raw image.jpg --format jpeg --no-jpeg-white-balance

Replace existing converted outputs:

.. code-block:: bash

   GONet_Wizard split_raw *.jpg --outdir converted --overwrite

GUI Equivalent
--------------

The graphical equivalent is :doc:`Split RAW Images GUI guide <../gui_guide/split_raw>`.

Related Pages
-------------

* :doc:`split RAW images tool guide <../tools/split_raw_images>`
* :doc:`GONet images user guide <../user_guide/gonet_images>`
* :doc:`GONetFile user guide <../user_guide/gonetfile>`
* :doc:`common CLI patterns <common_patterns>`
* :doc:`commands API reference <../api_reference/commands>`
