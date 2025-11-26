"""
This module defines the `Circle` class, which represents a circular sector shape
for pixel extraction. The `Circle` class is derived from the 
:class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class and provides
functionality for defining, validating, and manipulating circular sector shapes.

The `Circle` class is registered in the `Shape` framework via the 
:func:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.register` decorator, 
allowing dynamic instantiation based on the `shape` key in extraction parameters.

**Classes**

:class:`Circle`
    Represents a circular sector shape for pixel extraction, supporting operations such as
    mask generation, visualization, and parameter extraction.
    
"""

import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
import numpy as np
from GONet_Wizard.GONet_utils import DATA_SPEC
import matplotlib.axes

@base.Shape.register("circle")
class Circle(base.Shape):
    """
    Represents a circular sector shape for pixel extraction.

    The `Circle` class is derived from the :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class
    and provides functionality to define, validate, and manipulate circular sector shapes. It supports operations such as
    generating masks for pixel selection, creating Plotly-compatible shapes for visualization, and extracting parameters
    from dictionaries.

    The :func:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.register` decorator adds ``circle`` to the shape registry.

    """

    def __init__(self,
        x0: float,
        y0: float,
        radius: float,
        start_angle: float = -180,
        end_angle: float = 180
    ):
        """
        Initialize a Circle object with its geometric parameters.

        Parameters
        ----------
        shape_name : :class:`str`
            Name of the shape, set to "circle".
        x0 : :class:`float`
            X-coordinate of the center of the circle.
        y0 : :class:`float`
            Y-coordinate of the center of the circle.
        radius : :class:`float`
            Radius of the circle.
        start_angle : :class:`float`, optional
            Start angle of the circular sector in degrees (default: -180).
        end_angle : :class:`float`, optional
            End angle of the circular sector in degrees (default: 180).
        """
        self.shape_name = "circle"
        self.x0 = x0
        self.y0 = y0
        self.radius = radius
        self.start_angle = base.normalize_angle_deg(start_angle)
        self.end_angle = base.normalize_angle_deg(end_angle)
        self.validate()

    def validate(self) -> None:
        """
        Validate and convert the circle parameters.

        This method ensures that all parameters are numeric and converts
        string representations of numbers to floats.

        Raises
        ------
        :class:`.base.IncompleteShapeError`
            If any required parameter is missing.
        TypeError
            If any parameter is not a numeric type or a string representing a number.
        ValueError
            If radius is not positive or angles are out of range.
        """
        # Validate and convert numeric parameters
        for attr_name in ["x0", "y0", "start_angle", "end_angle"]:
            value = getattr(self, attr_name)
            self._validate_numeric(value, attr_name)
            setattr(self, attr_name, float(value))  # Convert to float if valid

        # Validate and convert radius
        self._validate_numeric(self.radius, "radius")
        self._validate_positive(self.radius, "radius")
        self.radius = float(self.radius)  # Convert to float if valid

    def get_extractor_field(self) -> dict:
        """
        Retrieve the extraction parameters as a dictionary.

        This method returns a dictionary containing the geometric parameters of the
        circular sector, mapped to their corresponding keys as defined in the `DATA_SPEC`.

        Returns
        -------
        :class:`dict`
            A dictionary with the following keys and their corresponding values:
            - `shape`: The name of the shape, set to "circle".
            - `x0`: X-coordinate of the center of the circle.
            - `y0`: Y-coordinate of the center of the circle.
            - `radius`: Radius of the circle.
            - `start_angle`: Start angle of the circular sector in degrees.
            - `end_angle`: End angle of the circular sector in degrees.

        Notes
        -----
        - This method is used to standardize the extraction parameters for use in the
          extraction pipeline.

        """
        return {
            DATA_SPEC['shape'].key : self.shape_name,
            DATA_SPEC['x0'].key : self.x0,
            DATA_SPEC['y0'].key : self.y0,
            DATA_SPEC['radius'].key : self.radius,
            DATA_SPEC['start_angle'].key : self.start_angle,
            DATA_SPEC['end_angle'].key : self.end_angle
        }

    def draw(self, n_segments: int = 60) -> list[dict]:
        """
        Generate Plotly-compatible shape(s) for a circular sector or full circle.

        This method creates a visual representation of the circular sector or full circle
        as Plotly-compatible shapes. The circular sector is approximated using a specified
        number of line segments for the arc.

        Parameters
        ----------
        n_segments : :class:`int`, optional
            Number of line segments to approximate the arc (default: 60).

        Returns
        -------
        :class:`list` of :class:`dict`
            A list of Plotly shape dictionaries representing the circular sector or full circle.

        """

        out_shape = base.plotly_shape.copy()

        angle_diff = self.end_angle - self.start_angle
        if angle_diff == 0 or angle_diff == 360:
            out_shape["type"] = "circle"
            out_shape["x0"] = self.x0 - self.radius
            out_shape["x1"] = self.x0 + self.radius
            out_shape["y0"] = self.y0 - self.radius
            out_shape["y1"] = self.y0 + self.radius

        else:
            arc_path = base.build_arc_path(self.x0, self.y0, self.radius, self.start_angle, self.end_angle, n_segments)
            path = f"M {self.x0},{self.y0} " + arc_path + "Z"

            out_shape["type"] = "path"
            out_shape["path"] = path

        return [out_shape]

    def plt_draw(self, ax: matplotlib.axes.Axes, **kwargs: dict) -> None:
        """
        Draw the circular sector on a Matplotlib Axes.

        This method adds a visual representation of the circular sector or full circle
        to the provided Matplotlib Axes object.

        Parameters
        ----------
        ax : :class:`matplotlib.axes.Axes`
            The Matplotlib Axes object to draw the shape on.
        **kwargs : :class:`dict`
            Additional keyword arguments to customize the appearance of the shape.

        Returns
        -------
        None

        """
        import matplotlib.patches as patches

        angle_diff = self.end_angle - self.start_angle
        if angle_diff == 0 or angle_diff == 360:
            circle = patches.Circle((self.x0, self.y0), self.radius, fill=False, **kwargs)
            ax.add_patch(circle)
        else:
            wedge = patches.Wedge(
                (self.x0, self.y0),
                self.radius,
                self.start_angle,
                self.end_angle,
                fill=False,
                **kwargs
            )
            ax.add_patch(wedge)

    def mask(self, data: np.ndarray | list) -> np.ndarray:
        """
        Create a boolean mask selecting pixels inside a circular sector.

        This method generates a 2D boolean mask where pixels inside the circular sector
        are marked as `True` and others as `False`. The circular sector is defined by
        its center, radius, and angular range.

        Parameters
        ----------
        data : :class:`numpy.ndarray` or :class:`list`
            2D array or nested list representing the image data.

        Returns
        -------
        :class:`numpy.ndarray`
            A boolean mask with the same shape as `data`, where `True` indicates
            pixels inside the circular sector.

        """
        data = np.asarray(data)
        ny, nx = data.shape
        x = np.arange(nx)
        y = np.arange(ny)
        xv, yv = np.meshgrid(x, y)

        dx = xv - self.x0
        dy = yv - self.y0
        r2 = dx**2 + dy**2
        
        # Detect full circle edge case (tolerate small numerical errors)
        if np.isclose((self.end_angle - self.start_angle) % 360, 0, atol=1e-5):
            return r2 <= self.radius**2

        angle = np.degrees(np.arctan2(dy, dx))  # Already in [-180, 180]

        if self.end_angle >= self.start_angle:
            angular_mask = (angle >= self.start_angle) & (angle <= self.end_angle)
        else:
            angular_mask = (angle >= self.start_angle) | (angle <= self.end_angle)

        radial_mask = r2 < self.radius**2
        return radial_mask & angular_mask

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create a Circle object from a dictionary of parameters.

        This method instantiates a `Circle` object using a dictionary containing
        the required geometric parameters.

        Parameters
        ----------
        data : :class:`dict`
            A dictionary containing the following keys:
            - `x0` (:class:`float`): X-coordinate of the center of the circle.
            - `y0` (:class:`float`): Y-coordinate of the center of the circle.
            - `param1` (:class:`float`): Radius of the circle.
            - `start_angle` (:class:`float`): Start angle of the circular sector in degrees.
            - `end_angle` (:class:`float`): End angle of the circular sector in degrees.

        Returns
        -------
        :class:`Circle`
            An instance of the `Circle` class initialized with the provided parameters.

        """
        return cls(data['x0'], data['y0'], data['param1'], data['start_angle'], data['end_angle'])