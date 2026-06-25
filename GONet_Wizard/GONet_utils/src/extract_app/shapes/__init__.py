"""
This subpackage defines a set of geometric shape classes used to describe regions of interest
in 2D images. These shapes support common operations such as:

- Construction from different parameterizations
- Validation of geometric properties
- Drawing and visualization
- Masking of NumPy arrays using the shape footprint

Each shape class inherits from a shared abstract base class that ensures a unified interface
for working with different geometries in the GONet ecosystem.

Submodules
----------
- :mod:`.base` :
    Defines the abstract base class :class:`Shape` and shared functionality for all shape types.
    Also defines the :class:`IncompleteShapeError` 

- :mod:`.circle` :
    Implements a circular region defined by a center point and radius.

- :mod:`.annulus` :
    Defines an annular (ring-shaped) region described by an inner and outer radius.

- :mod:`.path` :
    Represents a general closed path using SVG-style path strings. Used for rectangles too.
"""

from .base import Shape, IncompleteShapeError
from .circle import Circle
from .annulus import Annulus
from .path import Path

__all__ = ["Shape", "Circle", "Annulus", "Path", "IncompleteShapeError"]