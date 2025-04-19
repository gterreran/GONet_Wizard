"""
Provides basic circular aperture photometry tools for GONet images.

This module includes functionality to extract statistical measurements
from circular regions within 2D image arrays (e.g., total and mean counts,
standard deviation, and pixel count).

**Functions**

- :func:`extract_circle`: Compute statistics from a circular region of interest in an image.

**Classes**

- :class:`extraction_output`: A dataclass representing the result of a circular extraction.

"""

from dataclasses import dataclass
import numpy as np

@dataclass
class extraction_output:
    """
    Container for the results of a circular aperture extraction.

    Attributes
    ----------
    total_counts : :class:`float`
        Sum of pixel values within the circular region.

    mean_counts : :class:`float`
        Average of the pixel values within the circle.

    std : :class:`float`
        Standard deviation of the pixel values.

    npixels : :class:`int`
        Number of pixels within the circular region.
    """
    total_counts: float
    mean_counts: float
    std: float
    npixels: int

def extract_circle(data: np.ndarray, x0: float, y0: float, radius: float) -> extraction_output:
    """
    Perform circular aperture photometry on a 2D image array.

    Parameters
    ----------
    data : :class:`numpy.ndarray`
        2D array representing the image.

    x0 : :class:`float`
        X-coordinate of the circle center.

    y0 : :class:`float`
        Y-coordinate of the circle center.

    radius : :class:`float`
        Radius of the circular aperture.

    Returns
    -------
    :class:`extraction_output`
        Statistical measurements of the pixel values inside the circular aperture.
    """
    # Create coordinate arrays
    y = np.arange(0, data.shape[0])
    x = np.arange(0, data.shape[1])

    # Create a circular mask
    mask = (x[np.newaxis, :] - x0)**2 + (y[:, np.newaxis] - y0)**2 < radius**2

    # Extract statistics over the masked region
    return extraction_output(
        total_counts = np.sum(data[mask]),
        mean_counts = np.mean(data[mask]),
        std = np.std(data[mask]),
        npixels = len(data[mask])
    )
