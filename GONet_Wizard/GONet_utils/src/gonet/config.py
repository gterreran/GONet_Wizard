"""
Configuration constants defining the raw GONet camera specifications.

This module contains the fundamental constants describing the GONet camera's
sensor geometry and data layout. These parameters are used throughout the
GONet processing pipeline for decoding, reading, and reshaping the binary
image data stored in RAW `.jpg` files.

Constants
---------
RAW_FILE_OFFSET : :class:`int`
    Offset in bytes to the beginning of the raw data.
RAW_HEADER_SIZE : :class:`int`
    Size in bytes of the file header preceding the image data.
RAW_DATA_OFFSET : :class:`int`
    Effective offset to the start of image data, computed as
    ``RAW_FILE_OFFSET - RAW_HEADER_SIZE``.
RELATIVETOEND : :class:`int`
    File-seek flag indicating offset is relative to file end.
PIXEL_PER_LINE : :class:`int`
    Number of pixels per image row on the sensor.
PIXEL_PER_COLUMN : :class:`int`
    Number of pixels per image column on the sensor.
PADDED_LINE_BYTES : :class:`int`
    Number of bytes used to store each image row including padding.
USED_LINE_BYTES : :class:`int`
    Number of bytes actually containing pixel data
    (for 12-bit encoding, ``PIXEL_PER_LINE * 12 / 8``).
    
"""

RAW_FILE_OFFSET = 18711040
RAW_HEADER_SIZE = 32768
RAW_DATA_OFFSET = RAW_FILE_OFFSET - RAW_HEADER_SIZE
RELATIVETOEND = 2

PIXEL_PER_LINE = 4056
PIXEL_PER_COLUMN = 3040
PADDED_LINE_BYTES = 6112  # Including padding
USED_LINE_BYTES = int(PIXEL_PER_LINE * 12 / 8)