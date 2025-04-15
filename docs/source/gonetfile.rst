GONetFile Module
================

This module defines the `GONetFile` class, which provides functionality for 
handling and processing GONet files. The class encapsulates the properties 
and methods required for manipulating the image data (including red, green, 
and blue channels) and metadata associated with GONet files.

The module supports various operations on GONet files, including:
- Loading image data from original raw (`.jpg`) or TIFF formats.
- Performing arithmetic operations between GONet files and scalar values.
- Writing image data to common formats like JPEG, TIFF, and FITS.
- Parsing and handling metadata for different file types.

For more info regarding how the raw data is parsed, see :doc:`raw_data`.

The `GONetFile` class also includes support for operator overloading, allowing 
users to easily perform element-wise operations between GONet files or between 
a GONet file and scalar values.

Attributes
----------
The `GONetFile` class maintains the following key attributes:
- Red, green, and blue channel data as :mod:`numpy` arrays.
- Metadata associated with the file.
- File type information (e.g., SCIENCE, FLAT, etc.).

This module utilizes libraries like :mod:`numpy`, :mod:`PIL.Image`, and 
:mod:`astropy.io.fits` to perform various operations on image data and metadata.

Example usage:
--------------
.. code-block:: python

   gonet_file = GONetFile.from_file('example_image.tiff')
   plt.imshow(gonet_file.green)

Overview
--------------
.. automodule:: GONet_Wizard.GONet_utils.src.gonetfile
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: RAW_FILE_OFFSET, RAW_HEADER_SIZE, RAW_DATA_OFFSET, RELATIVETOEND, PIXEL_PER_LINE, PIXEL_PER_COLUMN, USED_LINE_BYTES, CHANNELS, __dict__, __module__, __weakref__
   :special-members:
   :private-members:
    
    