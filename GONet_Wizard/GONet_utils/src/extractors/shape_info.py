"""
Shape parameter extractor
=========================

This module defines the :class:`.ShapeInfo` extractor, which interprets and
standardizes geometric parameters used for pixel count extraction.

It converts the raw extraction configuration into shape-specific metadata
(e.g., circle radius, annulus width, center coordinates) using the
:mod:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base` framework.

**Classes**

:class:`.ShapeInfo`
    Extracts shape-specific parameters for pixel count extraction.
"""

from GONet_Wizard.GONet_utils.src.extractors.core import Extractor
from GONet_Wizard.GONet_utils.src.extract_app.shapes import base
from typing import Dict, Any, Tuple

class ShapeInfo(Extractor):
    """
    Extracts shape-specific parameters for pixel count extraction.

    This class inherits from the base :class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor`
    class and is responsible for processing shape-related extraction parameters.

    Attributes
    ----------
    USES : :class:`list`
        A list of context keys required by this extractor. For :class:`.ShapeInfo`, this is empty
        as it operates directly on the raw input.
    PROVIDES : :class:`list`
        A list of keys that this extractor provides to the extraction pipeline. For :class:`ShapeInfo`,
        this is empty as it only updates the shared context.

    """
    
    USES = []
    PROVIDES = []

    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract shape-specific parameters and update the shared context.

        This method processes the extraction parameters provided in `raw["extraction_parameters"]`
        to dynamically instantiate a :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` object and retrieve its metadata. While the raw
        dictionary contains generic parameters, their geometric meaning is determined by
        the specific shape type. The correct keys for the output dictionary are defined
        in each shape class.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. Must include the key "extraction_parameters",
            which is a dictionary of parameters specific to the shape. These parameters may
            include generic values (e.g., "radius", "center") that are mapped to shape-specific
            labels once the shape is determined.
        context : :class:`dict`
            A shared dictionary for intermediate results. This extractor does not modify the context.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with shape-specific metadata, including keys required for pixel count extraction.
            - The unchanged `context` dictionary.

        Raises
        ------
        :class:`ValueError`
            If the `extraction_parameters` key is missing or invalid in the raw input.

        Notes
        -----
        - The `extraction_parameters` dictionary must include a `shape` key specifying the type of shape.
        - Generic parameters in `extraction_parameters` (e.g., "param1", "param2") are mapped to shape-specific
          labels (e.g., "inner_radius", "outer_radius") based on the shape

        """
        shape = base.Shape.from_dict(raw["extraction_parameters"])

        results = {
            "files": raw["file_list"]
        }
        results.update(shape.get_extractor_field())

        return results, context