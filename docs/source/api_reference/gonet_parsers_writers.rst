GONet Parsers and Writers
=========================

File-format readers and writers used by :class:`GONetFile` and related command
workflows.

Parsers Package
---------------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.parsers
   :members:
   :show-inheritance:

EXIF Reader
-----------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.parsers.exif_reader
   :members:
   :show-inheritance:

RAW Reader
----------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.parsers.raw_reader
   :members:
   :show-inheritance:

TIFF Reader
-----------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.parsers.tiff_reader
   :members:
   :show-inheritance:

Writers Package
---------------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.writers
   :members:
   :show-inheritance:

FITS Writer
-----------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.writers.fits
   :members:
   :show-inheritance:

Writer white balance
--------------------

The JPEG and TIFF writers can apply white balance using gains stored in RAW
JPEG metadata. TIFF-loaded ``GONetFile`` objects normally do not have that
metadata, so callers that enable white balance for metadata-free images should
pass both ``red_gain`` and ``blue_gain`` explicitly. If neither metadata nor a
complete manual gain pair is available, the writers raise ``ValueError`` with a
recovery hint.

JPEG Writer
-----------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.writers.jpeg
   :members:
   :show-inheritance:

TIFF Writer
-----------

.. automodule:: GONet_Wizard.GONet_utils.src.gonet.writers.tiff
   :members:
   :show-inheritance:
