"""
Utility functions for low-level I/O and numeric data transformations used by GONet files.

This module contains helper routines that perform standard numeric conversions
and data handling for GONet raw files and related image-processing workflows.

The functions defined here are intended to be lightweight and dependency-free,
providing basic data scaling and consistency utilities used throughout
the :mod:`GONet_Wizard.GONet_utils` package.

**Functions**

- :func:`.scale_uint12_to_16bit_range`
    Linearly scale 12-bit unsigned integer values to the full 16-bit range [0, 65535].
"""

import numpy as np

def scale_uint12_to_16bit_range(x):
    """
    Linearly scales unsigned 12-bit integer values to the full 16-bit range [0, 65535].

    This function maps values from the uint12 range [0, 4095] to the float range [0, 65535],
    preserving relative magnitudes without rounding or type conversion to integer.

    Parameters
    ----------
    x : array-like or int
        Input value(s) in the uint12 range [0, 4095]. Can be a scalar or NumPy array.

    Returns
    -------
    np.ndarray or float
        Scaled value(s) in the float range [0.0, 65535.0]. Output dtype is float64.

    Raises
    ------
    ValueError
        If any input values are outside the valid uint12 range.

    """
    x = np.asarray(x)

    max_uint12 = 2**12 - 1  # 4095
    max_uint16 = 2**16 - 1  # 65535

    if np.any((x < 0) | (x > max_uint12)):
        raise ValueError(f"Input values must be in the range [0, {max_uint12}] for uint12.")

    scaled = (x / max_uint12) * max_uint16
    return scaled