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
ChannelName : :class:`typing.Literal`
    Type hint for channel names (raw or processed).
CHANNEL_NAMES_RAW : :class:`tuple` of :class:`str`
    Ordered tuple of RAW channel names: ('blue', 'green1', 'green2', 'red').
CHANNEL_NAMES_PROCESSED : :class:`tuple` of :class:`str`
    Ordered tuple of processed channel names: ('blue', 'green', 'red').

Functions
---------
get_channel_bayer_offsets : callable
    Returns the (row, col) offsets for a given channel in the BGGR Bayer pattern.
    
"""

from typing import Literal

RAW_FILE_OFFSET = 18711040
RAW_HEADER_SIZE = 32768
RAW_DATA_OFFSET = RAW_FILE_OFFSET - RAW_HEADER_SIZE
RELATIVETOEND = 2

PIXEL_PER_LINE = 4056
PIXEL_PER_COLUMN = 3040
PADDED_LINE_BYTES = 6112  # Including padding
USED_LINE_BYTES = int(PIXEL_PER_LINE * 12 / 8)

# Type hint for channel names
ChannelName = Literal["blue", "green", "green1", "green2", "red"]

# Actual tuples of channel names (for iteration, etc.)
CHANNEL_NAMES_RAW = ("blue", "green1", "green2", "red")
CHANNEL_NAMES_PROCESSED = ("blue", "green", "red")


def get_channel_bayer_offsets(channel: ChannelName) -> tuple[int, int]:
    """
    Get the row and column byte offsets for a channel in the BGGR Bayer pattern.
    
    Parameters
    ----------
    channel : ChannelName
        One of 'blue', 'green1', 'green2', or 'red'.
    
    Returns
    -------
    tuple of int
        (row_offset, col_offset) indicating the starting pixel location
        for the channel in the Bayer mosaic.
        
    Raises
    ------
    ValueError
        If the channel name is not recognized.

    """
    # BGGR pattern locations (even/odd are 0/1 parity)
    offsets = {
        "blue": (0, 0),      # even-even
        "green1": (0, 1),    # even-odd
        "green2": (1, 0),    # odd-even
        "red": (1, 1),       # odd-odd
    }
    
    if channel not in offsets:
        raise ValueError(
            f"Unknown channel '{channel}'. Must be one of: "
            f"{', '.join(offsets.keys())}"
        )
    
    return offsets[channel]