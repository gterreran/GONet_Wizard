"""
Derived color-column utilities for dashboard data.

The dashboard represents channel ratios as astronomical color-like quantities,
computed as ``2.5 * log10(a / b)``.  This module keeps that calculation in one
place so JSON and CSV dashboard inputs produce the same derived ``color_*``
columns after loading.

Functions
---------
:func:`color_from_channels`
    Compute a vectorized color value from two count arrays, returning
    ``NaN`` where either input is non-finite or non-positive.
"""

from __future__ import annotations
import numpy as np


def color_from_channels(a, b):
    """
    Vectorized 2.5 * log10(a / b) with NaN handling.

    Parameters
    ----------
    a : array-like
        First channel values.
    b : array-like
        Second channel values.
    
    Returns
    -------
    out : ndarray
        Array of color values computed as 2.5 * log10(a / b), with NaNs where
        inputs are invalid (non-finite or non-positive).
        
    """
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)

    out = np.full(np.broadcast(a_arr, b_arr).shape, np.nan, dtype=float)
    valid = (
        np.isfinite(a_arr)
        & np.isfinite(b_arr)
        & (a_arr > 0.0)
        & (b_arr > 0.0)
    )

    if valid.any():
        out[valid] = 2.5 * np.log10(a_arr[valid] / b_arr[valid])

    return out
