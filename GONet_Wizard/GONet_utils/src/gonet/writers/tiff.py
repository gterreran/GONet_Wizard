"""
Utility for exporting GONet image data to TIFF format.

This module provides a generic function, :func:`.write_to_tiff`, which writes
the RGB image data of a :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`
or :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw`
instance to a standard 16-bit TIFF file.

The function automatically handles both averaged-green and dual-green
(BGGR) inputs, applies optional white balance corrections from metadata,
and ensures values are safely clipped and cast to ``uint16`` for
TIFF compatibility.

**Functions**

- :func:`.write_to_tiff`
    Write GONet RGB data to a 16-bit TIFF file
"""

import numpy as np
import tifffile

def write_to_tiff(self, output_filename: str, white_balance: bool = True) -> None:
    """
    Write the RGB image data to a TIFF file.

    This method assumes that the blue, green, and red channels are in the
    uint16 range [0, 65535]. Values outside this range are clipped, and
    the data is cast to uint16 for TIFF compatibility.

    If ``white_balance`` is True, the method applies red and blue channel gains
    from ``self.meta['JPEG']['WB']`` prior to writing, in order to produce a 
    more natural-looking image. The white balance is expected to be a list 
    or tuple of two floats: [R_gain, B_gain].

    Parameters
    ----------
    output_filename : :class:`str`
        Path where the resulting TIFF file will be saved.

    white_balance : :class:`bool`, optional
        Whether to apply white balance using gains from metadata (default is True).

    Raises
    ------
    ValueError
        If ``white_balance`` is True but the WB metadata is missing or invalid.
    """
    blue  = self.blue.astype(np.float32)
    if hasattr(self, 'green1') and hasattr(self, 'green2'):
        green = ((self.green1.astype(np.float32) + self.green2.astype(np.float32)) / 2)
    else:
        green = self.green.astype(np.float32)
    red   = self.red.astype(np.float32)
    

    if white_balance:
        try:
            r_gain, b_gain = self.meta["JPEG"]["WB"]
            red *= r_gain
            blue *= b_gain
            # green remains unchanged
        except Exception as e:
            raise ValueError("White balance metadata 'WB' is missing or invalid.") from e

    rgb_stack = np.stack([
        np.clip(red, 0, 2**16 - 1).astype(np.uint16),
        np.clip(green, 0, 2**16 - 1).astype(np.uint16),
        np.clip(blue, 0, 2**16 - 1).astype(np.uint16)
    ], axis=0)

    tifffile.imwrite(output_filename, rgb_stack, photometric='rgb')