Split RAW Images
================

The **Split RAW Images** form converts original GONet RAW ``.jpg`` files into
standard TIFF and JPEG products from the graphical interface.

.. note::

   This page explains how to run RAW splitting from the GUI.

   To learn what the tool does, when to use TIFF versus JPEG outputs, and why
   the white-balance defaults differ, see :doc:`split RAW images tool guide <../tools/split_raw_images>`.

Overview
--------

The Split RAW Images form is used to select one or more original GONet RAW
``.jpg`` files, choose which converted products to write, and optionally choose a
base output directory.

The form is a graphical frontend for the ``split_raw`` command. The conversion
runs directly from the form and reports progress in the command feedback
terminal. It does not open a separate preview window because the command writes
files and does not produce an interactive visualization.

Selecting Files
---------------

The **RAW GONet JPG files or folders** field defines the input images.

Files can be selected in two ways.

Typing Paths
~~~~~~~~~~~~

Paths may be typed directly into the text field.

The field supports:

* Single file paths.
* Folder paths.
* Comma-separated entries.
* Wildcards.

This makes it possible to convert several files or groups of files without
using the file browser.

Browsing for Files
~~~~~~~~~~~~~~~~~~

The **Browse...** button opens a file picker.

Multiple files may be selected at once. When the selection is confirmed, the
selected paths are inserted into the input field automatically.

Output Directory
----------------

The **Optional output directory** field controls where converted products are
written.

If this field is left blank, products are written next to each input file.

If a directory is provided, GONet Wizard creates product-specific subfolders
inside that directory:

.. code-block:: text

   selected-output-directory/
   ├── tiffs/
   └── jpegs/

TIFF products are written to ``tiffs`` and JPEG products are written to
``jpegs``. This keeps large batch conversions organized and makes it easier to
use one product type in later workflows.

Output Products
---------------

The **Output products** selector controls which files are created.

Available choices are:

* **TIFF and JPEG** — write both product types. This is the default.
* **TIFF only** — write only ``.tiff`` products.
* **JPEG only** — write only ``.jpeg`` products.

TIFF products are the better default for scientific or quantitative follow-up.
JPEG products are intended for visual inspection and sharing.

White-Balance Controls
----------------------

The form exposes separate white-balance controls for TIFF and JPEG outputs.

**Apply white balance to TIFF outputs**
   Disabled by default.

   TIFF outputs may be used later for scientific extraction or quantitative
   checks. Leaving white balance off keeps pixel counts closer to the RAW data.

**Disable white balance for JPEG outputs**
   Disabled by default, meaning JPEG white balance is normally enabled.

   JPEG outputs are usually display products, so white balance is enabled by
   default to make them easier to inspect visually.

Overwrite Existing Outputs
--------------------------

The **Overwrite existing outputs** checkbox controls whether existing converted
files may be replaced.

By default, GONet Wizard refuses to overwrite existing files. This protects
previous conversions during batch runs. Enable overwrite only when you
intentionally want to regenerate outputs.

Running the Conversion
----------------------

To split RAW images from the GUI:

#. Select one or more original GONet RAW ``.jpg`` files or folders.
#. Optionally choose an output directory.
#. Choose the output products.
#. Adjust the white-balance checkboxes only if the defaults are not appropriate.
#. Enable overwrite only if existing products should be replaced.
#. Click **Split raw**.

The command feedback terminal shows the command submitted by the form and the
paths written by the conversion.

Feedback Terminal
-----------------

The Split RAW Images form uses the same command feedback terminal pattern as
other file-writing GUI commands.

The terminal shows:

* the command equivalent submitted by the form;
* progress, warnings, and errors;
* the input-to-output path summary after a successful conversion.

Because ``split_raw`` writes files and does not create an interactive preview,
no additional result window is opened after the command finishes.

Navigation Buttons
------------------

The buttons at the bottom of the window control the GUI session.

**Back to Main Menu**
   Returns to the launcher without running the current form.

**Exit**
   Closes the graphical interface.

Relationship to the CLI
-----------------------

The Split RAW Images form is the graphical frontend for the ``split_raw``
command.

Both interfaces use the same processing engine and produce the same TIFF/JPEG
products.

See Also
--------

* :doc:`split RAW images tool guide <../tools/split_raw_images>`
* :doc:`split_raw CLI reference <../cli_reference/split_raw>`
* :doc:`GONet images user guide <../user_guide/gonet_images>`
* :doc:`GONetFile user guide <../user_guide/gonetfile>`
* :doc:`GUI launcher guide <launcher>`
