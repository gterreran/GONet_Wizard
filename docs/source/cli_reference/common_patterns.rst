Common CLI Patterns
===================

Several GONet Wizard commands share the same input and option patterns.

This page summarizes those shared conventions so individual command pages can
focus on command-specific behavior.

Input Files and Folders
-----------------------

Many commands accept one or more input paths.

Depending on the command, inputs may be:

* individual files,
* folders,
* wildcard patterns,
* comma-separated lists.

In normal shell usage, quotation marks are usually not required.

For example, all of the following are valid input styles:

.. code-block:: bash

   GONet_Wizard show image1.jpg
   GONet_Wizard show image1.jpg image2.jpg
   GONet_Wizard show *.jpg
   GONet_Wizard show image1.jpg,image2.jpg
   GONet_Wizard show /path/to/folder/

When a folder is provided, GONet Wizard expands files from that folder
non-recursively.

Multiple Separate Paths
-----------------------

Multiple files may be provided as separate command-line arguments.

.. code-block:: bash

   GONet_Wizard show image1.jpg image2.jpg image3.jpg

This is often the clearest form when working with a small number of files.

Folders
-------

A folder may be provided directly.

.. code-block:: bash

   GONet_Wizard show /path/to/images/

GONet Wizard expands the folder contents and uses the files supported by the
command being run.

Wildcards
---------

Wildcard inputs are supported for many file-based commands.

.. code-block:: bash

   GONet_Wizard show *.jpg
   GONet_Wizard show AdlerRoof_*.jpg
   GONet_Wizard show_meta *.tiff
   GONet_Wizard extract data/*.tiff --shape circle --center 1000,800 --radius 50

In most interactive terminal sessions, the shell expands the wildcard before
GONet Wizard receives the arguments. This is valid and expected.

Quotation marks may still be useful when you want GONet Wizard itself to
perform the wildcard expansion instead of the shell:

.. code-block:: bash

   GONet_Wizard show "*.jpg"

Both quoted and unquoted wildcard patterns are valid in typical workflows.

Comma-Separated Lists
---------------------

Several commands also accept comma-separated path lists.

.. code-block:: bash

   GONet_Wizard show image1.jpg,image2.jpg
   GONet_Wizard show_meta image1.jpg,image2.jpg

Do not insert spaces after the commas unless each path is meant to be treated
as a separate shell argument.

Comma-separated lists are useful when passing several paths as one argument,
especially from scripts or GUI-generated command payloads.

Long Path Examples
------------------

The same input styles work with full paths.

These are all valid:

.. code-block:: bash

   GONet_Wizard show ~/Desktop/Work/data/GONet/Grainger/new/202/after_focus_new_calibration/*jpg

   GONet_Wizard show ~/Desktop/Work/data/GONet/Grainger/new/202/after_focus_new_calibration/

   GONet_Wizard show ~/Desktop/Work/data/GONet/Grainger/new/202/after_focus_new_calibration/202_250116_204846_1737060529.jpg,~/Desktop/Work/data/GONet/Grainger/new/202/after_focus_new_calibration/202_250116_204846_1737060545.jpg

   GONet_Wizard show ~/Desktop/Work/data/GONet/Grainger/new/202/after_focus_new_calibration/202_250116_204846_1737060529.jpg ~/Desktop/Work/data/GONet/Grainger/new/202/after_focus_new_calibration/202_250116_204846_1737060545.jpg

When Quotes Are Useful
----------------------

Quotation marks are optional in most examples, but they are useful when:

* a path contains spaces,
* a path contains shell-special characters,
* you want GONet Wizard, rather than the shell, to expand a wildcard,
* you are writing documentation where preserving the literal pattern matters.

For ordinary paths without spaces, folders, comma-separated lists, and common
wildcards, quotes are not needed.

Supported Image Extensions
--------------------------

Image-oriented commands generally filter inputs to supported GONet image
extensions.

Common supported extensions include:

* ``.jpg``
* ``.jpeg``
* ``.tiff``
* ``.tif``

The exact extension allowlist depends on the command.

Channel Flags
-------------

Several image-based commands accept Bayer channel flags.

Common channel flags are:

* ``--blue``
* ``--green``
* ``--red``

If no channel flags are provided, commands that operate on channels generally
use all available channels.

If one or more channel flags are provided, only those channels are used.

Output Paths
------------

Some commands write output products.

When providing output paths, use explicit filenames:

.. code-block:: bash

   GONet_Wizard show image.jpg --save preview.pdf
   GONet_Wizard extract image.jpg --shape circle --center 1000,800 --radius 50 --output counts.json

For extraction outputs, if the requested file already exists, GONet Wizard
creates a new filename with a numeric suffix rather than overwriting the
existing file.

GUI-Backed Commands from the CLI
--------------------------------

Some commands can open GUI windows even when launched from the terminal.

Examples include:

* ``GONet_Wizard gui``
* ``GONet_Wizard dashboard results/``
* ``GONet_Wizard extract image.jpg --shape interactive``

These commands use the shared UI runtime described in
:doc:`UI runtime developer notes <../developer_notes/ui_runtime>`.

Missing Required Arguments
--------------------------

For some command-only invocations, GONet Wizard may open the corresponding GUI
form instead of only printing a terminal error.

For example:

.. code-block:: bash

   GONet_Wizard show

can route to the Show Image GUI form because the command is valid but the
required file arguments are missing.

Command Form vs Interactive App Fallbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is an important distinction between opening a command form and launching
an interactive tool.

For example, ``GONet_Wizard extract`` opens the Extract GUI form because the
command was requested without the inputs needed to submit a complete run from
the terminal.

By contrast, ``GONet_Wizard extract image.jpg`` has enough information to start
an extraction workflow, but not enough information for direct geometric
extraction. In that case the interactive extraction app opens so the region can
be selected visually.

For more details, see :doc:`command-system developer notes <../developer_notes/command_system>`.
