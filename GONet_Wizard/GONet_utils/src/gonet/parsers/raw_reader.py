"""
Parser for GONet RAW `.jpg` image files.

This module defines :func:`.parse_raw_file`, which reads uncompressed RAW `.jpg`
files produced by GONet cameras and reconstructs the individual color channels
from the packed 12-bit Bayer data stored in the file.

The function unpacks the BGGR Bayer pattern into four subframes
(`blue`, `green1`, `green2`, `red`), rescales the data to the 16-bit range,
and returns the channel arrays in GONet's standard (B, G₁, G₂, R) order.

**Functions**

- :func:`.parse_raw_file`
    Parse a RAW `.jpg` file and extract blue, green1, green2, and red channel
    arrays as 16-bit scaled NumPy arrays.

**Classes**

- :class:`.RawFileReadError`
    Exception raised when a RAW file cannot be read due to format issues.

"""

import numpy as np
from GONet_Wizard.GONet_utils.src.gonet import config
from GONet_Wizard.GONet_utils.src.gonet.io_utils import scale_uint12_to_16bit_range


class RawFileReadError(ValueError):
    """
    Raised when a raw GONet file cannot be read due to invalid format/offsets.
    """
    pass


def parse_raw_file(
        filepath: str,
    ) -> np.ndarray:
    """
    Parse a raw GONet file and extract RGB channel data and optional metadata.

    This static method reads a GONet raw file—typically with a `.jpg` extension 
    but not in standard JPEG format—and extracts the blue, green, and red image 
    channels.

    Parameters
    ----------
    filepath : :class:`str`
        Path to the raw file to be parsed.
    
    Returns
    -------
    :class:``numpy.ndarray``
        A NumPy array of shape ``(3, H, W)`` representing the blue, green, and red channels.

    Raises
    ------
    FileNotFoundError
        If the file does not exist or is not accessible.
    ValueError
        If the file format is incompatible or corrupted.
    """
    try:
        with open(filepath, "rb") as file:
            file.seek(-config.RAW_DATA_OFFSET, config.RELATIVETOEND)
            s=np.zeros((config.PIXEL_PER_LINE, config.PIXEL_PER_COLUMN), dtype='uint16')
            # do this at least 3040 times though the precise number of lines is a bit unclear
            for i in range(config.PIXEL_PER_COLUMN):

                # read in 6112 bytes, but only 6084 will be used
                bdLine = file.read(config.PADDED_LINE_BYTES)
                gg = np.frombuffer(bdLine[0:config.USED_LINE_BYTES], dtype=np.uint8)
                s[0::2, i] = (gg[0::3].astype(np.uint16) << 4) + (gg[2::3].astype(np.uint16) & 15)
                s[1::2, i] = (gg[1::3].astype(np.uint16) << 4) + (gg[2::3].astype(np.uint16) >> 4)

        # form superpixel array
        sp=np.empty((int(config.PIXEL_PER_LINE/2),int(config.PIXEL_PER_COLUMN/2),4))
        
        # Extract channels using BGGR pattern offsets
        for i, channel in enumerate(config.CHANNEL_NAMES_RAW):
            row_offset, col_offset = config.get_channel_bayer_offsets(channel)
            sp[:, :, i] = s[row_offset::2, col_offset::2]

        array=scale_uint12_to_16bit_range(sp.transpose())

        return array

    except OSError as e:
        # Includes invalid seek (Errno 22), unreadable file, etc.
        raise RawFileReadError(f"{filepath}: {e}") from e