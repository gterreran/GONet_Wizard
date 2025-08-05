"""
This module provides utilities for defining and extracting regions of interest
from 2D image arrays using geometric masks. It includes tools for building boolean
masks from circular sectors, annular sectors, and SVG-style polygonal paths.

**Functions**

- :func:`normalize_angle_deg`:
    Normalizes a given angle to the range [-180, 180] degrees.
    
- :func:`normalize_start_end_angles`:
    A decorator that automatically normalizes the `start_angle` and `end_angle` 
    arguments of decorated functions to the range [-180, 180].

- :func:`mask_sector`:
    Create a mask for a circular sector defined by a center, radius, and angular range.

- :func:`mask_annular_sector`:
    Create a mask for an annular (ring-shaped) sector with inner and outer radius and angle limits.

- :func:`mask_from_closed_path`:
    Generate a mask from a closed SVG path string (e.g., from a Plotly shape).

- :func:`parse_svg_path`:
    Parse (x, y) vertices from an SVG-style 'path' string (e.g., 'M x,y L x,y ... Z').
    
- :func:`extract_region`:
    Compute statistics (sum, mean, std, count) from a masked region in an image.
    
**Classes**

- :class:`extraction_output`: A dataclass representing the result of a circular extraction.

"""

import re, inspect
from matplotlib.path import Path
from dataclasses import dataclass
import numpy as np
from functools import wraps
from typing import Callable

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


def normalize_angle_deg(angle: float) -> float:
    """
    Normalize an angle in degrees to the range [-180, 180], inclusive.

    Parameters
    ----------
    angle : :class:`float`
        Input angle in degrees.

    Returns
    -------
    :class:`float`
        Normalized angle in the range [-180, 180].
    """
    angle = angle % 360
    if angle == 180:
        return 180.0
    elif angle == 0:
        return 0.0
    elif angle > 180:
        return angle - 360
    else:
        return angle


def normalize_start_end_angles(func: Callable) -> Callable:
    """
    Decorator that normalizes 'start_angle' and 'end_angle' arguments
    to the range [-180, 180] degrees before calling the function.

    Works for both positional and keyword arguments.

    Parameters
    ----------
    func : :class:`Callable`
        The function to wrap. It must accept 'start_angle' and 'end_angle' as arguments.

    Returns
    -------
    :class:`Callable`
        A wrapped version of `func` with normalized angle inputs.
    """
    sig = inspect.signature(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Bind arguments to their names
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for name in ("start_angle", "end_angle"):
            if name in bound_args.arguments:
                bound_args.arguments[name] = normalize_angle_deg(bound_args.arguments[name])

        return func(*bound_args.args, **bound_args.kwargs)

    return wrapper


@normalize_start_end_angles
def mask_sector(data: np.ndarray | list, x0: float, y0: float, radius: float,
                start_angle: float, end_angle: float) -> np.ndarray:
    """
    Create a boolean mask selecting pixels inside a circular sector.

    Parameters
    ----------
    data : :class:`numpy.ndarray` or :class:`list`
        2D image array or nested list representing the image.

    x0 : :class:`float`
        X-coordinate of the sector center.

    y0 : :class:`float`
        Y-coordinate of the sector center.

    radius : :class:`float`
        Radius of the sector.

    start_angle : :class:`float`
        Start angle in degrees (range must be [-180, 180]). Angle is measured
        counter-clockwise from the x-axis.

    end_angle : :class:`float`
        End angle in degrees (range must be [-180, 180]). Angle is measured
        counter-clockwise from the x-axis.

    Returns
    -------
    :class:`numpy.ndarray`
        Boolean mask with True for pixels inside the sector.
    """
    data = np.asarray(data)
    ny, nx = data.shape
    x = np.arange(nx)
    y = np.arange(ny)
    xv, yv = np.meshgrid(x, y)

    dx = xv - x0
    dy = yv - y0
    r2 = dx**2 + dy**2
    angle = np.degrees(np.arctan2(dy, dx))  # Already in [-180, 180]

    if end_angle >= start_angle:
        angular_mask = (angle >= start_angle) & (angle <= end_angle)
    else:
        angular_mask = (angle >= start_angle) | (angle <= end_angle)

    radial_mask = r2 < radius**2
    return radial_mask & angular_mask


@normalize_start_end_angles
def mask_annular_sector(data: np.ndarray | list, x0: float, y0: float,
                        r_inner: float, r_outer: float,
                        start_angle: float, end_angle: float) -> np.ndarray:
    """
    Create a boolean mask selecting pixels inside an annular sector.

    Parameters
    ----------
    data : :class:`numpy.ndarray` or :class:`list`
        2D image array or nested list representing the image.

    x0 : :class:`float`
        X-coordinate of the annular sector center.

    y0 : :class:`float`
        Y-coordinate of the annular sector center.

    r_inner : :class:`float`
        Inner radius of the annular sector (excluded).

    r_outer : :class:`float`
        Outer radius of the annular sector (included).

    start_angle : :class:`float`
        Start angle in degrees (range must be [-180, 180]).
        Angle is measured counter-clockwise from the x-axis.

    end_angle : :class:`float`
        End angle in degrees (range must be [-180, 180]).
        Angle is measured counter-clockwise from the x-axis.

    Returns
    -------
    :class:`numpy.ndarray`
        Boolean mask with True for pixels inside the annular sector.
    """
    data = np.asarray(data)
    ny, nx = data.shape
    x = np.arange(nx)
    y = np.arange(ny)
    xv, yv = np.meshgrid(x, y)

    dx = xv - x0
    dy = yv - y0
    r2 = dx**2 + dy**2
    angle = np.degrees(np.arctan2(dy, dx))  # range [-180, 180]

    # Angular mask
    if end_angle >= start_angle:
        angular_mask = (angle >= start_angle) & (angle <= end_angle)
    else:
        angular_mask = (angle >= start_angle) | (angle <= end_angle)

    # Radial mask (annulus)
    radial_mask = (r2 >= r_inner**2) & (r2 <= r_outer**2)

    return radial_mask & angular_mask


def parse_svg_path(path_str: str) -> np.ndarray:
    """
    Extract vertices from a Plotly SVG 'path' string like 'M x,y L x,y ... Z'.

    Parameters
    ----------
    path_str : :class:`str`
        SVG-style path string from a Plotly shape.

    Returns
    -------
    :class:`numpy.ndarray`
        Nx2 array of (x, y) vertex coordinates.
    """
    coords = re.findall(r"[ML]\s*([\d\.]+),([\d\.]+)", path_str)
    return np.array([[float(x), float(y)] for x, y in coords])


def mask_from_closed_path(data: np.ndarray | list, path_str: str) -> np.ndarray:
    """
    Create a boolean mask selecting pixels inside a closed SVG path.

    Parameters
    ----------
    data : :class:`numpy.ndarray` or :class:`list`
        2D image array or nested list representing the image.

    path_str : :class:`str`
        Path string from a Plotly shape (in SVG format).

    Returns
    -------
    :class:`numpy.ndarray`
        Boolean mask with True for pixels inside the closed path.
    """
    data = np.asarray(data)
    ny, nx = data.shape
    poly = parse_svg_path(path_str)

    # Create a grid of all (x, y) pixel centers
    x = np.arange(nx)
    y = np.arange(ny)
    xv, yv = np.meshgrid(x, y)
    points = np.vstack((xv.ravel(), yv.ravel())).T

    # Evaluate inclusion
    path = Path(poly)
    mask = path.contains_points(points).reshape((ny, nx))
    return mask


def extract_region(data: np.ndarray | list, mask: np.ndarray) -> extraction_output:
    """
    Compute statistics for pixels selected by a mask.

    Parameters
    ----------
    data : :class:`numpy.ndarray` or :class:`list`
        2D image array.

    mask : :class:`numpy.ndarray`
        Boolean array of the same shape as `data` indicating which pixels to include.

    Returns
    -------
    :class:`extraction_output`
        Statistical summary of pixel values in the masked region.
    """
    values = np.array(data)[mask]
    return extraction_output(
        total_counts = np.sum(values),
        mean_counts = np.mean(values),
        std = np.std(values),
        npixels = values.size
    )
