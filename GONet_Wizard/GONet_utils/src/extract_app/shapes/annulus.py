"""
This module defines the `Annulus` class, which represents an annular sector shape
for pixel extraction. The `Annulus` class is derived from the 
:class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class and provides
functionality for defining, validating, and manipulating annular sector shapes.

The `Annulus` class is registered in the `Shape` framework via the `@Shape.register("annulus")` 
decorator, allowing dynamic instantiation based on the `shape` key in extraction parameters.

**Classes**

:class:`Annulus`
    Represents an annular sector shape for pixel extraction, supporting operations such as
    mask generation, visualization, and parameter extraction.
"""

import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
import numpy as np
from GONet_Wizard.GONet_utils.src.data_spec import DATA_SPEC

@base.Shape.register("annulus")
class Annulus(base.Shape):
    """
    Represents an annular sector shape for pixel extraction.

    The `Annulus` class is derived from the :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class 
    and provides functionality to define, validate, and manipulate annular sector shapes. It supports operations such as 
    generating masks for pixel selection, creating Plotly-compatible shapes for visualization, and extracting parameters 
    from dictionaries.

    The :func:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.register` decorator adds ``annulus`` to the shape registry.

    """
    def __init__(self,
        x0: float,
        y0: float,
        inner_radius: float,
        outer_radius: float,
        start_angle: float = -180,
        end_angle: float = 180
    ):
        """
        Initialize an Annulus object with its geometric parameters.

        Parameters
        ----------
        x0 : :class:`float`
            X-coordinate of the center of the annulus.
        y0 : :class:`float`
            Y-coordinate of the center of the annulus.
        inner_radius : :class:`float`
            Inner radius of the annulus (excluded from the region).
        outer_radius : :class:`float`
            Outer radius of the annulus (included in the region).
        start_angle : :class:`float`, optional
            Start angle of the annular sector in degrees (default: -180).
        end_angle : :class:`float`, optional
            End angle of the annular sector in degrees (default: 180).
        """
        self.x0 = x0
        self.y0 = y0
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.start_angle = base.normalize_angle_deg(start_angle)
        self.end_angle = base.normalize_angle_deg(end_angle)
        self.validate()

    def validate(self) -> None:
        """
        Validate and convert the annular sector parameters.

        This method ensures that all parameters are numeric and converts
        string representations of numbers to floats.

        Raises
        ------
        :class:`.base.IncompleteShapeError`
            If any required parameter is missing.
        TypeError
            If any parameter is not a numeric type or a string representing a number.
        ValueError
            If radii are not positive or if outer_radius is not greater than inner_radius.
        """
        # Validate and convert numeric parameters
        for attr_name in ["x0", "y0", "start_angle", "end_angle"]:
            value = getattr(self, attr_name)
            self._validate_numeric(value, attr_name)
            setattr(self, attr_name, float(value))  # Convert to float if valid

        # Validate and convert radii
        for attr_name in ["inner_radius", "outer_radius"]:
            value = getattr(self, attr_name)
            self._validate_numeric(value, attr_name)
            self._validate_positive(value, attr_name)
            setattr(self, attr_name, float(value))  # Convert to float if valid

        # Ensure outer_radius is greater than inner_radius
        if self.outer_radius <= self.inner_radius:
            raise ValueError("outer_radius must be greater than inner_radius.")

    def get_extractor_field(self) -> dict:
        """
        Retrieve the extraction parameters as a dictionary.

        This method returns a dictionary containing the geometric parameters of the
        annular sector, mapped to their corresponding keys as defined in the `DATA_SPEC`.

        Returns
        -------
        :class:`dict`
            A dictionary with the following keys and their corresponding values:
            - `x0`: X-coordinate of the center of the annulus.
            - `y0`: Y-coordinate of the center of the annulus.
            - `inner_radius`: Inner radius of the annulus.
            - `outer_radius`: Outer radius of the annulus.
            - `start_angle`: Start angle of the annular sector in degrees.
            - `end_angle`: End angle of the annular sector in degrees.

        Notes
        -----
        - This method is used to standardize the extraction parameters for use in the
        extraction pipeline.
        
        """
        return {
            DATA_SPEC['x0'].key : self.x0,
            DATA_SPEC['y0'].key : self.y0,
            DATA_SPEC['inner_radius'].key : self.inner_radius,
            DATA_SPEC['outer_radius'].key : self.outer_radius,
            DATA_SPEC['start_angle'].key : self.start_angle,
            DATA_SPEC['end_angle'].key : self.end_angle
        }

    def draw(self, n_segments: int = 60) -> list[dict]:
        """
        Generate Plotly-compatible shape(s) for an annular sector using straight line segments.

        This method creates a visual representation of the annular sector or full annulus
        as Plotly-compatible shapes. The annular sector is approximated using a specified
        number of line segments for the arcs.

        Parameters
        ----------
        n_segments : :class:`int`, optional
            Number of line segments to approximate each arc (default: 60).

        Returns
        -------
        :class:`list` of :class:`dict`
            A list of Plotly shape dictionaries representing the annular sector or full annulus.

        Raises
        ------
        ValueError
            If the radii are not positive or if `inner_radius` is greater than or equal to `outer_radius`.
        """
        if self.inner_radius <= 0 or self.outer_radius <= 0:
            raise ValueError("Radii must be positive.")
        if self.inner_radius >= self.outer_radius:
            raise ValueError("inner_radius must be smaller than outer_radius.")
        
        out_shape = base.plotly_shape.copy()

        angle_diff = self.end_angle - self.start_angle

        if angle_diff == 0:
            # Return two full circles to represent a complete annulus
            out_shape["type"] = "circle"
            inner_circle = out_shape.copy()
            outer_circle = out_shape.copy()

            inner_circle["x0"] = self.x0 - self.inner_radius
            inner_circle["x1"] = self.x0 + self.inner_radius
            inner_circle["y0"] = self.y0 - self.inner_radius
            inner_circle["y1"] = self.y0 + self.inner_radius

            outer_circle["x0"] = self.x0 - self.outer_radius
            outer_circle["x1"] = self.x0 + self.outer_radius
            outer_circle["y0"] = self.y0 - self.outer_radius
            outer_circle["y1"] = self.y0 + self.outer_radius

            return [inner_circle, outer_circle]

        # Build arc paths
        outer_arc = base.build_arc_path(self.x0, self.y0, self.outer_radius, self.start_angle, self.end_angle, n_segments)
        inner_arc = base.build_arc_path(self.x0, self.y0, self.inner_radius, self.end_angle, self.start_angle, n_segments)  # reversed arc

        # Starting point (outer arc start)
        theta0 = np.radians(self.start_angle)
        xstart = self.x0 + self.outer_radius * np.cos(theta0)
        ystart = self.y0 + self.outer_radius * np.sin(theta0)

        path = f"M {xstart},{ystart} "
        path += outer_arc
        path += inner_arc
        path += "Z"

        out_shape["type"] = "path"
        out_shape["path"] = path

        return [out_shape]
    
    def mask(self, data: np.ndarray | list) -> np.ndarray:
        """
        Create a boolean mask selecting pixels inside the annular sector.

        This method generates a 2D boolean mask for an annular sector, where pixels
        inside the defined region are marked as `True` and others as `False`. The
        annular sector is defined by its center, inner and outer radii, and angular range.

        Parameters
        ----------
        data : :class:`numpy.ndarray` or :class:`list`
            2D array or nested list representing the image data.

        Returns
        -------
        :class:`numpy.ndarray`
            A boolean mask with the same shape as `data`, where `True` indicates
            pixels inside the annular sector.
        """
        data = np.asarray(data)
        ny, nx = data.shape
        x = np.arange(nx)
        y = np.arange(ny)
        xv, yv = np.meshgrid(x, y)

        dx = xv - self.x0
        dy = yv - self.y0
        r2 = dx**2 + dy**2

        # Radial mask (annulus)
        radial_mask = (r2 >= self.inner_radius**2) & (r2 <= self.outer_radius**2)

        if np.isclose((self.end_angle - self.start_angle), 0, atol=1e-5):
            # Full circle, skip angular mask
            return radial_mask

        angle = np.degrees(np.arctan2(dy, dx))  # range [-180, 180]

        # Angular mask
        if self.end_angle >= self.start_angle:
            angular_mask = (angle >= self.start_angle) & (angle <= self.end_angle)
        else:
            angular_mask = (angle >= self.start_angle) | (angle <= self.end_angle)

        return radial_mask & angular_mask

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create an Annulus object from a dictionary of parameters.

        This method instantiates an `Annulus` object using a dictionary containing
        the required geometric parameters.

        Parameters
        ----------
        data : :class:`dict`
            A dictionary containing the following keys:
            - `x0` (:class:`float`): X-coordinate of the center of the annulus.
            - `y0` (:class:`float`): Y-coordinate of the center of the annulus.
            - `param1` (:class:`float`): Inner radius of the annulus.
            - `param2` (:class:`float`): Outer radius of the annulus.
            - `start_angle` (:class:`float`): Start angle of the annular sector in degrees.
            - `end_angle` (:class:`float`): End angle of the annular sector in degrees.

        Returns
        -------
        :class:`Annulus`
            An instance of the `Annulus` class initialized with the provided parameters.

        """
        return cls(data['x0'], data['y0'], data['param1'], data['param2'], data['start_angle'], data['end_angle'])