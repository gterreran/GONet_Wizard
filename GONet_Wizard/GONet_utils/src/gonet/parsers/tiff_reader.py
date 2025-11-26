"""
Parser for TIFF image files used in GONet data processing.

This module defines a function, :func:`.parse_tiff_file`, which reads TIFF images
and extracts the RGB channel data in the expected GONet format. The function
automatically reorders the color channels from the TIFF storage order (R, G, B)
to the standard GONet convention (B, G, R).

**Functions**

- :func:`.parse_tiff_file`
    Parse a TIFF file and return the blue, green, and red channel arrays as NumPy arrays.
"""

import numpy as np
from tifffile import tifffile

def parse_tiff_file(filepath: str) -> np.ndarray:
    """
    Parse a TIFF file and extract RGB channel data and optional metadata.

    This static method reads a TIFF file and separates the image into blue, green, 
    and red channels.

    Parameters
    ----------
    filepath : :class:`str`
        Path to the TIFF file to be parsed.

    Returns
    -------
    :class:``numpy.ndarray``
        A NumPy array of shape ``(3, H, W)`` representing the blue, green, and red channels.

    Raises
    ------
    FileNotFoundError
        If the file does not exist or is not accessible.
    ValueError
        If the TIFF file does not contain 3 channels.
    """

    with tifffile.TiffFile(filepath) as tif:
        tiff_data = tif.asarray()
        r, g, b = tiff_data
        return b, g, r