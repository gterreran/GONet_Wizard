"""
This module defines the `Path` class, which represents a generic path shape for pixel extraction.
The `Path` class is derived from the :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class
and provides functionality for defining, validating, and manipulating path-based shapes. It supports operations
such as generating masks for pixel selection, creating Plotly-compatible shapes for visualization, and extracting
parameters from dictionaries.

The `Path` class is registered in the `Shape` framework via the 
:func:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.register` decorator, with the aliases 
`path`, `freehand`, and `rectangle`. This allows dynamic instantiation of `Path` objects based on the `shape` key 
in extraction parameters.

**Classes**

:class:`Path`
    Represents a generic path shape for pixel extraction, supporting operations such as mask generation,
    visualization, and parameter extraction.
"""

import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
from matplotlib.path import Path as MatplotlibPath
import numpy as np
import re
from GONet_Wizard.GONet_utils.src.data_spec import DATA_SPEC

@base.Shape.register('path','freehand', 'rectangle')
class Path(base.Shape):
    """
    Represents a generic path shape for pixel extraction.

    The `Path` class is derived from the :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class
    and provides functionality to define, validate, and manipulate path shapes. It supports operations such as
    generating masks for pixel selection, creating Plotly-compatible shapes for visualization, and extracting parameters
    from dictionaries.

    The :func:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.register` decorator adds ``path``,
    ``freehand``, and ``rectangle`` to the shape registry.

    A rectangle shape will be Path shape, instantiated using the :func:`from_rectangle` class method.

    """
    def __init__(self, path_str: str):
        """
        Initialize a Path object from an SVG path string.

        Parameters
        ----------
        path_str : :class:`str`
            SVG path string defining the shape.
        """
        self.path_str = path_str
        self.validate()

    def validate(self) -> None:
        """
        Validate the SVG path string.

        Raises
        ------
        :class:`.base.IncompleteShapeError`
            If the path string is :class:`None`.
        TypeError
            If the path string is not a string.
        ValueError
            If the path string is malformed or does not match the SVG path format.
        """
        self._validate_defined(self.path_str, "path")

        SVG_PATH_PATTERN = re.compile(r'^([MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*)+$')

        if not isinstance(self.path_str, str):
            raise TypeError("SVG path must be a string.")

        if not SVG_PATH_PATTERN.match(self.path_str.strip()):
            raise ValueError("Malformed SVG path string.")

    def get_extractor_field(self) -> dict:
        """
        Retrieve the extraction parameters as a dictionary.

        This method returns a dictionary containing the SVG path string, mapped to its
        corresponding key as defined in the `DATA_SPEC`.

        Returns
        -------
        :class:`dict`
            A dictionary with the following key and its corresponding value:
            - `path`: The SVG path string defining the shape.

        Notes
        -----
        - This method is used to standardize the extraction parameters for use in the
          extraction pipeline.

        """
        return {
            DATA_SPEC['path'].key: self.path_str
        }

    @classmethod
    def from_rectangle(cls, x0: float, y0: float, side1: float, side2: float, start_angle: float = -180, end_angle: float = 180) -> "Path":
        """
        Generate an SVG path for a rectangular sector.

        Parameters
        ----------
        x0 : :class:`float`
            X-coordinate of the center.
        y0 : :class:`float`
            Y-coordinate of the center.
        side1 : :class:`float`
            Side 1 length.
        side2 : :class:`float`
            Side 2 length.
        start_angle : :class:`float`
            Start angle in degrees.
        end_angle : :class:`float`
            End angle in degrees.

        Returns
        -------
        :class:`Path`
            A Path object initialized with the SVG path string for the rectangular sector.

        Raises
        ------
        TypeError
            If any parameter is not a numeric type or a string representing a number.
        ValueError
            If side lengths are not positive or angles are invalid.
        """
    # Validate and convert numeric parameters
        for par, label in [(x0, "x0"), (y0, "y0"), (start_angle, "start_angle"), (end_angle, "end_angle")]:
            cls._validate_numeric(par, label)
            par = float(par)  # Convert to float

        # Validate and convert side lengths
        for par, label in [(side1, "side1"), (side2, "side2")]:
            cls._validate_numeric(par, label)
            cls._validate_positive(par, label)
            par = float(par)  # Convert to float

        # Normalize angles
        start_angle = base.normalize_angle_deg(start_angle)
        end_angle = base.normalize_angle_deg(end_angle)

        # Rectangle corners: bottom-left → bottom-right → top-right → top-left
        corners_x = [x0 - side1 / 2, x0 + side1 / 2, x0 + side1 / 2, x0 - side1 / 2]
        corners_y = [y0 - side2 / 2, y0 - side2 / 2, y0 + side2 / 2, y0 + side2 / 2]

        angle_diff = end_angle - start_angle
        order = 1 if angle_diff > 0 else -1

        # Handle full rectangle case
        if angle_diff == 0 or angle_diff == 360:
            path = f"M {corners_x[0]},{corners_y[0]} " + \
                   f"L {corners_x[1]},{corners_y[1]} " + \
                   f"L {corners_x[2]},{corners_y[2]} " + \
                   f"L {corners_x[3]},{corners_y[3]} Z"
        else:
            corner_vectors = [(-side1 / 2, -side2 / 2), (side1 / 2, -side2 / 2),
                              (side1 / 2, side2 / 2), (-side1 / 2, side2 / 2)]
            corners_angles = [
                base.normalize_angle_deg(np.degrees(np.arctan2(dy, dx))) for dx, dy in corner_vectors
            ]

            def intersection(angle_deg):
                """Find where a ray at angle_deg intersects the rectangle edges."""
                tan_a = np.tan(np.radians(angle_deg))
                if angle_deg < corners_angles[0] or angle_deg > corners_angles[3]:
                    x = x0 - side1 / 2
                    y = y0 - side1 / 2 * tan_a
                elif angle_deg < corners_angles[1]:
                    x = x0 - side2 / 2 / tan_a
                    y = y0 - side2 / 2
                elif angle_deg < corners_angles[2]:
                    x = x0 + side1 / 2
                    y = y0 + side1 / 2 * tan_a
                elif angle_deg < corners_angles[3]:
                    x = x0 + side2 / 2 / tan_a
                    y = y0 + side2 / 2
                return x, y

            start_x, start_y = intersection(start_angle)
            end_x, end_y = intersection(end_angle)

            path = f"M {x0},{y0} L {start_x},{start_y} "

            if order == 1:
                index_order = [0, 1, 2, 3]
            else:
                index_order = [2, 3, 0, 1]

            for i in index_order:
                if order == 1:
                    if corners_angles[i] > start_angle and corners_angles[i] < end_angle:
                        path += f"L {corners_x[i]},{corners_y[i]} "
                else:
                    if corners_angles[i] > start_angle or corners_angles[i] < end_angle:
                        path += f"L {corners_x[i]},{corners_y[i]} "

            path += f"L {end_x},{end_y} Z"

        return cls(path)
    

    def draw(self) -> list[dict]:
        """
        Generate a Plotly-compatible shape for the path.

        This method creates a visual representation of the path as a Plotly-compatible
        shape. The path is defined using the SVG path string stored in the object.

        Returns
        -------
        :class:`list` of :class:`dict`
            A list containing a single Plotly shape dictionary with the following properties:
            - `type`: Set to "path".
            - `path`: The SVG path string defining the shape.

        """
        
        out_shape = base.plotly_shape.copy()
        out_shape["type"] = "path"
        out_shape["path"] = self.path_str

        return [out_shape]

    def mask(self, data: np.ndarray | list) -> np.ndarray:
        """
        Create a boolean mask selecting pixels inside a closed SVG path.

        This method generates a 2D boolean mask where pixels inside the closed path
        defined by the SVG path string are marked as `True`, and others as `False`.

        Parameters
        ----------
        data : :class:`numpy.ndarray` or :class:`list`
            2D array or nested list representing the image data.

        Returns
        -------
        :class:`numpy.ndarray`
            A boolean mask with the same shape as `data`, where `True` indicates
            pixels inside the closed path.

        """
        data = np.asarray(data)
        ny, nx = data.shape
        coords = re.findall(r"[ML]\s*([\d\.]+),([\d\.]+)", self.path_str)
        poly = np.array([[float(x), float(y)] for x, y in coords])

        # Create a grid of all (x, y) pixel centers
        x = np.arange(nx)
        y = np.arange(ny)
        xv, yv = np.meshgrid(x, y)
        points = np.vstack((xv.ravel(), yv.ravel())).T

        # Evaluate inclusion
        path = MatplotlibPath(poly)
        mask = path.contains_points(points).reshape((ny, nx))
        return mask
    
    @classmethod
    def from_dict(cls, data: dict):
        """
        Create a Path object from a dictionary of parameters.

        This method dynamically creates a `Path` object based on the `shape` key in the
        provided dictionary. If the `shape` is "rectangle", the `from_rectangle` method
        is used to generate the path. Otherwise, the `path` key is used to initialize
        the object with an SVG path string.

        Parameters
        ----------
        data : :class:`dict`
            A dictionary containing the following keys:
            - `shape` (:class:`str`): The type of shape (e.g., "path", "freehand", "rectangle").
            - `path` (:class:`str`, optional): The SVG path string defining the shape (required for "path" or "freehand").
            - `x0` (:class:`float`, optional): X-coordinate of the center (required for "rectangle").
            - `y0` (:class:`float`, optional): Y-coordinate of the center (required for "rectangle").
            - `param1` (:class:`float`, optional): Side 1 length (required for "rectangle").
            - `param2` (:class:`float`, optional): Side 2 length (required for "rectangle").
            - `start_angle` (:class:`float`, optional): Start angle in degrees (required for "rectangle").
            - `end_angle` (:class:`float`, optional): End angle in degrees (required for "rectangle").

        Returns
        -------
        :class:`Path`
            A `Path` object initialized with the provided parameters.

        Raises
        ------
        KeyError
            If required keys are missing from the dictionary.
        ValueError
            If the `shape` key is not recognized or the parameters are invalid.

        """
    
        if data['shape'] == 'rectangle':
            return cls.from_rectangle(data['x0'], data['y0'], data['param1'], data['param2'], data['start_angle'], data['end_angle'])
        
        return cls(data['path'])