"""
This module provides functions to generate Plotly-compatible shape dictionaries 
for circular sectors, annular sectors, and rectangular sectors. These shapes are 
rendered using SVG path strings or basic circle primitives and are suitable for 
interactive visualizations in Dash or Plotly applications.

**Functions**

- :func:`build_arc_path`:
    Creates an SVG arc segment as a sequence of straight lines between given angles.

- :func:`sector_path`:
    Generates a circular sector from a center, radius, and angular bounds.
    
- :func:`rectangle_sector_path`:
    Defines a wedge-shaped portion of a rectangle, interpreted as bounded by 
    angular sectors of its circumscribed circle.

- :func:`annulus_sector_path`:
    Produces an annular (ring-shaped) sector between two radii and angular bounds.

All shapes assume angles are measured in degrees, with 0 degrees pointing along 
the positive x-axis, and increasing counterclockwise.

"""

import numpy as np
from GONet_Wizard.GONet_utils.src.extract import normalize_angle_deg, normalize_start_end_angles

def build_arc_path(cx: float, cy: float, r: float, start_angle: float, end_angle: float, n_segments: int = 60) -> str:
    """
    Generate the SVG path string for a circular arc using straight line segments.

    Parameters
    ----------
    cx : :class:`float`
        X-coordinate of the circle center.
    cy : :class:`float`
        Y-coordinate of the circle center.
    r : :class:`float`
        Radius of the arc.
    start_angle : :class:`float`
        Starting angle in degrees.
    end_angle : :class:`float`
        Ending angle in degrees.
    n_segments : :class:`int`
        Number of line segments to use for arc approximation.

    Returns
    -------
    :class:`str`
        SVG path fragment using only 'L' commands, starting from the first point on the arc.
    """
    theta0 = np.radians(start_angle)
    theta1 = np.radians(end_angle)
    thetas = np.linspace(theta0, theta1, n_segments + 1)

    xs = cx + r * np.cos(thetas)
    ys = cy + r * np.sin(thetas)

    path = f"L {xs[0]},{ys[0]} "  # Start from first arc point
    for x, y in zip(xs[1:], ys[1:]):
        path += f"L {x},{y} "
    return path


# Automatically normalizes angles to [-180, 180]
@normalize_start_end_angles
def sector_path(cx: float, cy: float, r: float, start_angle: float = -180, end_angle: float = 180, n_segments: int = 60) -> list[dict]:
    """
    Generate a Plotly-compatible SVG path for a circular sector using straight lines.

    Parameters
    ----------
    cx : :class:`float`
        X-coordinate of the circle center.
    cy : :class:`float`
        Y-coordinate of the circle center.
    r : :class:`float`
        Radius of the circle.
    start_angle : :class:`float`
        Start angle in degrees (default: -180).
    end_angle : :class:`float`
        End angle in degrees (default: 180).
    n_segments : :class:`int`
        Number of line segments to approximate the arc.

    Returns
    -------
    :class:`list` of :class:`dict`
        A list of Plotly shape dictionaries representing the circular sector or full circle.
    """

    angle_diff = end_angle - start_angle
    if angle_diff == 0 or angle_diff == 360:
        return [{
            "type": "circle",
            "x0": cx - r, "x1": cx + r,
            "y0": cy - r, "y1": cy + r,
            "line": {"color": "RoyalBlue"},
            "fillcolor": "rgba(65, 105, 225, 0.3)",
            "opacity": 1,
        }]

    arc_path = build_arc_path(cx, cy, r, start_angle, end_angle, n_segments)
    path = f"M {cx},{cy} " + arc_path + "Z"

    return [{
        "type": "path",
        "path": path,
        "line": {"color": "RoyalBlue"},
        "fillcolor": "rgba(65, 105, 225, 0.3)",
        "opacity": 1,
    }]


# Automatically normalizes angles to [-180, 180]
@normalize_start_end_angles
def rectangle_sector_path(
    rx: float,
    ry: float,
    s1: float,
    s2: float,
    start_angle: float = -180,
    end_angle: float = 180,
) -> list[dict]:
    """
    Generate a Plotly-compatible SVG path for a rectangular sector.

    Parameters
    ----------
    rx : :class:`float`
        X-coordinate of the center.
    ry : :class:`float`
        Y-coordinate of the center.
    s1 : :class:`float`
        Side 1 length.
    s2 : :class:`float`
        Side 2 length.
    start_angle : :class:`float`
        Start angle in degrees.
    end_angle : :class:`float`
        End angle in degrees.

    Returns
    -------
    :class:`list` of :class:`dict`
        A list of Plotly shape dictionaries representing the rectangular sector or full rectangle.
    """

    print(start_angle,end_angle)

    # Rectangle corners: bottom-left → bottom-right → top-right → top-left
    corners_x = [rx - s1 / 2, rx + s1 / 2, rx + s1 / 2, rx - s1 / 2]
    corners_y = [ry - s2 / 2, ry - s2 / 2, ry + s2 / 2, ry + s2 / 2]

    angle_diff = end_angle - start_angle
    # Determining if we need the long or the shor arc
    order = 1 if angle_diff > 0 else -1

    # Handle full rectangle case
    if angle_diff == 0 or angle_diff == 360:
        path = f"M {corners_x[0]},{corners_y[0]} " + \
               f"L {corners_x[1]},{corners_y[1]} " + \
               f"L {corners_x[2]},{corners_y[2]} " + \
               f"L {corners_x[3]},{corners_y[3]} Z"

    else:
        corner_vectors = [(-s1 / 2, -s2 / 2), (s1 / 2, -s2 / 2),
                          (s1 / 2, s2 / 2), (-s1 / 2, s2 / 2)]
        # Corners angles in the range [-180, 180]
        corners_angles = [
            normalize_angle_deg(np.degrees(np.arctan2(dy, dx))) for dx, dy in corner_vectors
        ]

        def intersection(angle_deg):
            """Find where a ray at angle_deg intersects the rectangle edges."""
            tan_a = np.tan(np.radians(angle_deg))
            if angle_deg < corners_angles[0]  or angle_deg > corners_angles[3]:
                x = rx - s1/2
                y = ry - s1/2 * tan_a
            elif angle_deg < corners_angles[1]:
                x = rx - s2/2 / tan_a
                y = ry - s2/2
            elif angle_deg < corners_angles[2]:
                x = rx + s1/2
                y = ry + s1/2 * tan_a
            elif angle_deg < corners_angles[3]:
                x = rx + s2/2 / tan_a
                y = ry + s2/2
            return x,y
        
        start_x, start_y = intersection(start_angle)
        end_x, end_y = intersection(end_angle)

        # Initializing the path
        path = f"M {rx},{ry} L {start_x},{start_y} "

        # If start and end are flipped, the sequence of
        # the corners need to be changed, making top right
        # the index 0 and then all the others counterclockwise.
        if order == 1:
            index_order = [0,1,2,3]
        else:
            index_order = [2,3,0,1]

        # Adding vertices in the right order.
        for i in index_order:
            if order == 1:
                if corners_angles[i] > start_angle and corners_angles[i] < end_angle:
                    path += f"L {corners_x[i]},{corners_y[i]} "
            else:
                if corners_angles[i] > start_angle or corners_angles[i] < end_angle:
                    path += f"L {corners_x[i]},{corners_y[i]} "
        
        # Finilizing the path
        path += f"L {end_x},{end_y} Z"


    return [
        {
            "type": "path",
            "path": path,
            "line": {"color": "RoyalBlue"},
            "fillcolor": "rgba(65, 105, 225, 0.3)",
            "opacity": 1,
        }
    ]


# Automatically normalizes angles to [-180, 180]
@normalize_start_end_angles
def annulus_sector_path(
    cx: float,
    cy: float,
    r_outer: float,
    r_inner: float,
    start_angle: float = -180,
    end_angle: float = 180,
    n_segments: int = 60,
) -> list[dict]:
    """
    Generate Plotly-compatible shape(s) for an annular sector using straight line segments.

    Parameters
    ----------
    cx : :class:`float`
        X-coordinate of the center.
    cy : :class:`float`
        Y-coordinate of the center.
    r_outer : :class:`float`
        Outer radius of the annulus.
    r_inner : :class:`float`
        Inner radius of the annulus (must be smaller than r_outer).
    start_angle : :class:`float`
        Start angle in degrees (default: -180).
    end_angle : :class:`float`
        End angle in degrees (default: 180).
    n_segments : :class:`int`
        Number of line segments to approximate each arc.

    Returns
    -------
    :class:`list` of :class:`dict`
        A list of Plotly shape dictionaries representing the annular sector or full ring.
    """
    if r_inner <= 0 or r_outer <= 0:
        raise ValueError("Radii must be positive.")
    if r_inner >= r_outer:
        raise ValueError("r_inner must be smaller than r_outer.")
    
    angle_diff = end_angle - start_angle

    if angle_diff == 0:
        # Return two full circles to represent a complete annulus
        return [
            {
                "type": "circle",
                "x0": cx - r_outer,
                "x1": cx + r_outer,
                "y0": cy - r_outer,
                "y1": cy + r_outer,
                "line": {"color": "RoyalBlue"},
                # "fillcolor": "rgba(65, 105, 225, 0.3)",
                "opacity": 1,
            },
            {
                "type": "circle",
                "x0": cx - r_inner,
                "x1": cx + r_inner,
                "y0": cy - r_inner,
                "y1": cy + r_inner,
                "line": {"color": "RoyalBlue"},  # Optional visual cutout
                "opacity": 1,
            }
        ]

    # Build arc paths
    outer_arc = build_arc_path(cx, cy, r_outer, start_angle, end_angle, n_segments)
    inner_arc = build_arc_path(cx, cy, r_inner, end_angle, start_angle, n_segments)  # reversed arc

    # Starting point (outer arc start)
    theta0 = np.radians(start_angle)
    x0 = cx + r_outer * np.cos(theta0)
    y0 = cy + r_outer * np.sin(theta0)

    path = f"M {x0},{y0} "
    path += outer_arc
    path += inner_arc
    path += "Z"

    return [
        {
            "type": "path",
            "path": path,
            "line": {"color": "RoyalBlue"},
            "fillcolor": "rgba(65, 105, 225, 0.3)",
            "opacity": 1,
        }
    ]

