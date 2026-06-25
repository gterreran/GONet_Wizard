"""
Definition of standard file type categories used in GONet observations.

This module provides the :class:`FileType` enumeration, which defines the
standard types of frames produced by GONet cameras. These file type labels
are used throughout the GONet processing pipeline to identify the purpose
of each file—whether it represents science data, calibration frames, or
instrumental corrections.

**Classes**

- :class:`FileType` : Enumeration of file types used in GONet observations (e.g., science, flat, bias, dark).
"""

from enum import Enum, auto

class FileType(Enum):
    """
    Enumeration of file types used in GONet observations.

    This enum defines the standard types of data that a GONet file may represent,
    used for categorizing the file during processing or analysis.

    Attributes
    ----------
    SCIENCE : :class:`FileType`
        Represents a science frame (standard observational data).
    FLAT : :class:`FileType`
        Represents a flat field frame (used for pixel response correction).
    BIAS : :class:`FileType`
        Represents a bias frame (used for sensor readout offset correction).
    DARK : :class:`FileType`
        Represents a dark frame (used to correct for dark current noise).
    """
    
    SCIENCE = auto()  # Represents science data
    FLAT = auto()     # Represents flat field data
    BIAS = auto()     # Represents bias data
    DARK = auto()     # Represents dark frame data