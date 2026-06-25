"""
Shape framework for interactive and scripted extraction regions
===============================================================

This module defines the abstract :class:`.Shape` API used by both the extraction
GUI and the command-line extraction pipeline.  Shape subclasses validate their
own geometry, draw Plotly/Matplotlib representations, and create boolean masks
that select pixels from an image channel.

Shape objects can be constructed directly by their subclasses or indirectly via
:meth:`Shape.from_dict`, which reads the ``"shape"`` key from an extraction
parameter dictionary.  This is the path used by the extraction command and the
interactive GUI when they pass user-selected regions to the extractor pipeline.

Classes
-------
:class:`.IncompleteShapeError`
    Raised when a required shape parameter is missing.
:class:`.Shape`
    Abstract base class and registry for all extraction-region shapes.

Functions
---------
:func:`.normalize_angle_deg`
    Normalize angles to the ``[-180, 180]`` degree range.
:func:`.build_arc_path`
    Approximate a circular arc as an SVG path string.
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Optional, Union
import math
import matplotlib.axes


plotly_shape = {
    "line": {"color": "red"},
    #"fillcolor": "rgba(65, 105, 225, 0.3)",
    "opacity": 1
}


class IncompleteShapeError(Exception):
    """
    Exception raised when a required shape parameter is not defined.

    This error is used to indicate that a shape parameter, which is expected to be provided
    for the proper functioning of a shape-related operation, is missing or set to `None`.
    """
    pass


class Shape(ABC):
    """
    Abstract base class for geometric shapes used in extraction operations.

    The `Shape` class provides a framework for defining and working with geometric shapes
    such as circles, rectangles, and paths. Subclasses must implement methods for validation,
    drawing, masking, and extracting fields.

    Attributes
    ----------
    _registry : :class:`dict`
        A class-level dictionary that maps shape type strings (e.g., "circle", "annulus",
        "rectangle") to their corresponding shape subclasses. Rectangles are handled by the
        path subclass. This registry allows dynamic instantiation
        of shape objects based on their type.

    Notes
    -----
    Subclasses must use the :meth:`Shape.register` decorator to register themselves with
    the registry.

    """
    _registry = {}

    def __init__(self, **params):
        """
        Store shape parameters for subclass-specific validation and masking.

        Parameters
        ----------
        **params
            Shape-specific parameters such as center coordinates, radii,
            vertices, or angle limits. Subclasses interpret and validate these
            values in their own :meth:`validate` implementations.

        Returns
        -------
        None
        """
        self.params = params

    @abstractmethod
    def get_extractor_field(self) -> dict:
        """
        Provide the keys and parameters required for pixel count extraction.

        This method is implemented by subclasses of :class:`.Shape` to return a dictionary
        containing the parameters necessary for
        :class:`~GONet_Wizard.GONet_utils.src.extractors.extraction_values.ExtractionValues`
        to perform pixel count extraction. The keys in the returned dictionary must match
        the expected structure defined in :data:`GONet_Wizard.GONet_utils.DATA_SPEC`.

        Returns
        -------
        :class:`dict`
            A dictionary containing the shape-specific parameters required for extraction.
            The keys correspond to the fields expected by
            :class:`~GONet_Wizard.GONet_utils.src.extractors.extraction_values.ExtractionValues`.

        Notes
        -----
        - Subclasses of :class:`Shape` must implement this method to provide the correct
          parameters for their specific geometry (e.g., circle, annulus, path).
        - Rectangular regions are represented by the path subclass.
        - :class:`~GONet_Wizard.GONet_utils.src.extractors.extraction_values.ExtractionValues`
          uses these parameters to generate masks and compute statistics for pixel values
          within the defined shape.

        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """
        Validate the parameters of the shape.

        This method should be implemented by subclasses to ensure that all required
        parameters are properly defined and meet the shape-specific constraints.

        Raises
        ------
        :class:`IncompleteShapeError`
            If any required parameter is missing or undefined.
        :class:`TypeError`
            If any parameter is not of the expected type.
        :class:`ValueError`
            If any parameter fails validation (e.g., negative values).

        """
        pass

    @abstractmethod
    def draw(self, n_segments: int = 60) -> list[dict]:
        """
        Draw the shape.

        This method should be implemented by subclasses to return a list of dictionaries
        representing the shapes. Each dictionary corresponds to a closed shape.

        Parameters
        ----------
        n_segments : :class:`int`, optional
            Number of line segments to use for approximating curved shapes (e.g., arcs).
            Defaults to 60.

        Returns
        -------
        :class:`list`[:class:`dict`]
            A list of dictionaries representing the shapes' geometry.

        Notes
        -----
        - This method is used for visualization or integration with external tools (e.g., Plotly).

        """
        pass

    @abstractmethod
    def plt_draw(self, ax: matplotlib.axes.Axes, **kwargs: dict) -> None:
        """
        Draw the shape on a Matplotlib Axes.

        This method should be implemented by subclasses to render the shape on the
        provided Matplotlib Axes object.

        Parameters
        ----------
        ax : :class:`matplotlib.axes.Axes`
            The Matplotlib Axes object on which to draw the shape.
        **kwargs : :class:`dict`
            Additional keyword arguments to customize the appearance of the shape.

        Returns
        -------
        None

        Notes
        -----
        - This method is used for visualization within Matplotlib plots.

        """
        pass

    @abstractmethod
    def mask(self, image: np.ndarray | list) -> np.ndarray:
        """
        Create a boolean mask for pixels inside the shape.

        This method should be implemented by subclasses to return a NumPy array
        representing a mask where pixels inside the shape are marked as `True` and
        pixels outside the shape are marked as `False`.

        Parameters
        ----------
        image : :class:`numpy.ndarray` or :class:`list`
            The input image or array to apply the mask to, typically the channel of
            a GONet image.

        Returns
        -------
        :class:`numpy.ndarray`
            A boolean array where `True` indicates pixels inside the shape.

        """
        pass

    @classmethod
    def register(cls, *shape_types: str):
        """
        Register a shape subclass with one or more type aliases.

        This method is used to associate a shape subclass with specific type strings
        (e.g., "circle", "rectangle") in the `_registry` dictionary. The `_registry`
        allows dynamic instantiation of shape objects based on their type strings.

        Parameters
        ----------
        shape_types : :class:`str`
            One or more type aliases for the shape subclass. These aliases are used
            to identify the shape type when creating instances dynamically.

        Returns
        -------
        :class:`function`
            A decorator function that registers the subclass with the provided aliases.
        
        Notes
        -----
        - Subclasses must use this decorator to register themselves with the `_registry`.
        - The `CLASS_ALIASES` attribute is added to the subclass, containing the
          registered shape type aliases.

        """
        def decorator(subclass):
            # Register each alias
            for shape_type in shape_types:
                cls._registry[shape_type] = subclass
            # Save the aliases directly on the subclass
            subclass.CLASS_ALIASES = list(shape_types)
            return subclass
        return decorator

    @classmethod
    def from_dict(cls, data: dict) -> "Shape":
        """
        Create a shape instance from a dictionary of parameters.

        This method dynamically instantiates a shape object based on the `shape` key
        in the provided dictionary. The `shape` key must correspond to one of the
        registered shape types in the `_registry`.

        Parameters
        ----------
        data : :class:`dict`
            A dictionary containing the parameters for the shape. The dictionary must
            include a `shape` key specifying the type of shape (e.g., "circle", "rectangle").
            Additional keys in the dictionary are passed to the shape subclass for initialization.

        Returns
        -------
        :class:`.Shape`
            An instance of the appropriate shape subclass, initialized with the parameters
            from the dictionary.

        Raises
        ------
        :class:`ValueError`
            If the `shape` key is missing or if the specified shape type is not registered.

        Notes
        -----
        - Subclasses must implement their own `from_dict` method to handle initialization
          from the dictionary.

        """
        shape_type = data["shape"]

        if shape_type not in cls._registry:
            raise ValueError(f"Unknown shape type: {shape_type}")
        return cls._registry[shape_type].from_dict(data)

    @staticmethod
    def _validate_defined(value: Optional[float], name: str) -> None:
        """
        Validate that a parameter is defined (not None).

        This method checks whether a parameter has been provided and is not `None`.
        It is typically used to ensure that required shape parameters are initialized
        before performing operations like validation, drawing, or masking.

        Parameters
        ----------
        value : Optional[:class:`float`]
            The value of the parameter to validate. Can be `None` or a numeric value.
        name : :class:`str`
            The name of the parameter (used in error messages).

        Raises
        ------
        :class:`IncompleteShapeError`
            If the parameter value is `None`.

        Notes
        -----
        - This method is typically called by other validation methods (e.g., `_validate_numeric`)
          to ensure that parameters are defined before further checks are performed.

        """
        if value is None:
            raise IncompleteShapeError(f"ERROR - '{name}' not defined.")

    @staticmethod
    def _validate_numeric(value: Union[float, int, str], name: str) -> None:
        """
        Validate that a parameter is numeric (int, float, or a string representing a number).

        Parameters
        ----------
        value : Union[:class:`float`, :class:`int`, :class:`str`]
            The value to validate.
        name : :class:`str`
            The name of the parameter (used in error messages).

        Raises
        ------
        :class:`IncompleteShapeError`
            If the value is None.
        :class:`TypeError`
            If the value is not a number or a string representing a number.
        :class:`ValueError`
            If the value is not finite.
        """
        Shape._validate_defined(value, name)

        # Attempt to convert strings to numbers
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                raise TypeError(f"ERROR - '{name}' is not a number.")

        if not isinstance(value, (int, float)):
            raise TypeError(f"ERROR - '{name}' is not a number.")
        if not math.isfinite(value):
            raise ValueError(f"ERROR - '{name}' is not finite.")

    @staticmethod
    def _validate_positive(value: Union[float, int], name: str) -> None:
        """
        Validate that a parameter is positive.

        This method checks whether a numeric parameter is greater than zero. It is typically
        used to ensure that parameters such as radius, side lengths, or other positive
        quantities meet the required constraints.

        Parameters
        ----------
        value : Union[:class:`float`, :class:`int`]
            The value of the parameter to validate.
        name : :class:`str`
            The name of the parameter (used in error messages).

        Raises
        ------
        :class:`IncompleteShapeError`
            If the value is `None`.
        :class:`TypeError`
            If the value is not a numeric type.
        :class:`ValueError`
            If the value is not positive.

        Notes
        -----
        - This method calls `_validate_numeric` to ensure the parameter is numeric before
          checking its positivity.
          
        """
        Shape._validate_numeric(value, name)
        if float(value) <= 0:
            raise ValueError(f"ERROR - '{name}' <= 0.")


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


def build_arc_path(x0: float, y0: float, r: float, start_angle: float, end_angle: float, n_segments: int = 60) -> str:
    """
    Generate the SVG path string for a circular arc using straight line segments.

    Parameters
    ----------
    x0 : :class:`float`
        X-coordinate of the circle center.
    y0 : :class:`float`
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

    xs = x0 + r * np.cos(thetas)
    ys = y0 + r * np.sin(thetas)

    path = f"L {xs[0]},{ys[0]} "  # Start from first arc point
    for x, y in zip(xs[1:], ys[1:]):
        path += f"L {x},{y} "
    return path