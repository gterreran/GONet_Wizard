"""
Utility for exporting GONet image data to JPEG format.

This module defines a convenience function, :func:`.write_to_jpeg`, for saving
the RGB image data of a :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`
or :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw`
instance as a standard 8-bit JPEG image.

The function automatically handles both single-green (averaged) and dual-green
(BGGR) channel configurations, applies optional white balance corrections from
metadata, rescales pixel values from 16-bit to 8-bit, and ensures the output is
clipped and properly formatted for JPEG encoding.

**Functions**

- :func:`.write_to_jpeg`
    Write GONet RGB data to an 8-bit JPEG file

"""

import numpy as np
from PIL import Image

def write_to_jpeg(self, output_filename: str, white_balance: bool = True) -> None:
    """
    Write the RGB image data to a JPEG file.

    This method assumes that the blue, green, and red channels are in the
    uint16 range [0, 65535], and rescales them to the standard 8-bit range
    [0, 255] required for JPEG output. Values outside this range are clipped,
    and the data is converted to 8-bit for JPEG compatibility.

    If ``white_balance`` is True, the method applies red and blue channel gains
    from ``self.meta['JPEG']['WB']`` prior to conversion, in order to produce a 
    more natural-looking image. The white balance is expected to be a list 
    or tuple of two floats: [R_gain, B_gain].

    Parameters
    ----------
    output_filename : :class:`str`
        Path where the resulting JPEG file will be saved.

    white_balance : :class:`bool`, optional
        Whether to apply white balance using gains from metadata (default is False).

    Raises
    ------
    ValueError
        If ``white_balance`` is True but the WB metadata is missing or invalid.
    """
    def convert_to_uint8(arr):
        arr = np.clip(arr, 0, 2**16 - 1)
        return np.round(arr / (2**16 - 1) * 255).astype(np.uint8)

    blue  = self.blue.astype(np.float32)
    if hasattr(self, 'green1') and hasattr(self, 'green2'):
        green = ((self.green1.astype(np.float32) + self.green2.astype(np.float32)) / 2)
    else:
        green = self.green.astype(np.float32)
    red   = self.red.astype(np.float32)

    # Apply white balance if requested
    if white_balance:
        try:
            r_gain, b_gain = self.meta["JPEG"]["WB"]
            red   *= r_gain
            blue  *= b_gain
            # green *= 1.0 (implicitly)
        except Exception as e:
            raise ValueError("White balance metadata 'WB' is missing or invalid.") from e

    # Convert to uint8 and stack
    rgb = np.stack([
        convert_to_uint8(red),
        convert_to_uint8(green),
        convert_to_uint8(blue)
    ], axis=-1)

    image = Image.fromarray(rgb, mode="RGB")
    image.save(output_filename, format="JPEG", quality=100)