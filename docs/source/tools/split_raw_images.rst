Split RAW Images
================

The split RAW images tool converts original GONet RAW ``.jpg`` files into
standard TIFF and JPEG image products.

This is useful because a GONet RAW ``.jpg`` file is not just an ordinary photo.
It is a container that includes a display JPEG component, a packed RAW Bayer
data block, and metadata. The split RAW workflow uses GONet Wizard's file parser
to read the RAW content and write conventional image files that are easier to
use outside the original container.

Typical Uses
------------

Use this tool when you want to:

* create standard TIFF files from original GONet RAW images;
* create standard JPEG files for quick visual inspection or sharing;
* prepare portable products for tools that do not understand the GONet RAW JPEG
  container;
* separate scientific-style products from display-oriented products;
* batch-convert folders of RAW GONet images.

Supported Inputs
----------------

The tool accepts original GONet RAW ``.jpg`` files.

Although the output JPEG products use the ``.jpeg`` extension, those converted
``.jpeg`` files are not valid inputs to ``split_raw``. They are standard display
products, not RAW GONet containers. Already converted ``.tiff`` files are also
not inputs to this command.

Output Products
---------------

The tool can write two product types.

TIFF Products
~~~~~~~~~~~~~

TIFF products are intended to preserve more of the sensor-level information
available from the RAW data.

By default, TIFF outputs are written without white balance. This default is
intentional: if the TIFF may later be used for scientific extraction,
calibration checks, or quantitative comparisons, the safest behavior is to keep
pixel counts as close as possible to the original RAW data rather than applying
visual channel gains.

Use TIFF products when the output may remain part of a measurement workflow.

JPEG Products
~~~~~~~~~~~~~

JPEG products are standard 8-bit display images.

By default, JPEG outputs are written with white balance enabled. This default is
also intentional: JPEGs are usually used for visual inspection, documentation,
sharing, or quick quality checks, where a visually interpretable color balance is
more useful than raw-like channel scaling.

Use JPEG products when the output is meant to be viewed rather than measured.

White-Balance Defaults
----------------------

The TIFF and JPEG defaults are different because the two products serve
different purposes.

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Product
     - Default white balance
     - Reason
   * - TIFF
     - Off
     - Preserve raw-like pixel counts for scientific extraction and quantitative workflows.
   * - JPEG
     - On
     - Produce visually useful images for inspection, sharing, and documentation.

Both defaults can be changed. The CLI exposes ``--tiff-white-balance`` and
``--no-jpeg-white-balance``. The GUI exposes matching checkbox controls.

Output Organization
-------------------

When no output directory is supplied, converted products are written next to the
input file:

.. code-block:: text

   image.jpg
   image.tiff
   image.jpeg

When an output directory is supplied, the tool creates dedicated product
subfolders:

.. code-block:: text

   converted/
   ├── tiffs/
   │   └── image.tiff
   └── jpegs/
       └── image.jpeg

The subfolder layout keeps mixed product types organized during batch
conversion. It also makes it easier to pass only TIFFs or only JPEGs to a later
workflow.

Overwrite Safety
----------------

The split RAW workflow does not overwrite existing products by default.

This conservative behavior is useful during batch processing because a command
may generate many outputs at once. Refusing existing output paths helps prevent
accidental replacement of earlier conversions. Use the overwrite option only
when you intentionally want to regenerate products.

Accessing the Tool
------------------

The split RAW images tool can be accessed through both the graphical user
interface and the command-line interface.

See:

* :doc:`Split RAW Images GUI guide <../gui_guide/split_raw>`
* :doc:`split_raw CLI reference <../cli_reference/split_raw>`

Where to Go Next
----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Need
     - Page
   * - Launch conversion from the GUI
     - :doc:`Split RAW Images GUI guide <../gui_guide/split_raw>`
   * - Run conversion from the terminal
     - :doc:`split_raw CLI reference <../cli_reference/split_raw>`
   * - Understand GONet RAW image containers
     - :doc:`GONet images user guide <../user_guide/gonet_images>`
   * - Understand the file object used by the converter
     - :doc:`GONetFile user guide <../user_guide/gonetfile>`
   * - Review the command implementation API
     - :doc:`commands API reference <../api_reference/commands>`

Related Topics
--------------

* :doc:`image inspection tool guide <inspect_images>`
* :doc:`extraction tool guide <extract_measurements>`
* :doc:`channels user guide <../user_guide/channels>`
