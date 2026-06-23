"""
Pipeline runner and public extraction API
=========================================

This module provides the public orchestration entry point for the extraction
subsystem.  The main function, :func:`.extract_all`, accepts a list of GONet
image files, channel names, and shape/extraction parameters, then runs the
configured extractor pipeline and returns one dictionary per retained file.

The runner combines two kinds of extractors:

- lightweight metadata extractors, such as file, time, astronomy, weather, and
  shape metadata;
- the heavier :class:`.ExtractionValues` extractor, which opens images and
  computes masked pixel statistics.

When :class:`.ExtractionValues` is present, it runs in a separate worker thread
while the lightweight metadata extractors run sequentially.  The individual
outputs are merged through :func:`.merge_extractor_into_data`, preserving
filepath alignment via the ``"files"`` key.

Attributes
----------
ALL_EXTRACTORS : :class:`list` of :class:`.Extractor`
    Default extractor sequence used by :func:`.extract_all`.

Functions
---------
:func:`.extract_all`
    Run the extraction pipeline and return JSON-serializable row dictionaries.
:func:`.convert_to_serializable`
    Convert NumPy scalar/array objects to plain Python values.
"""


from GONet_Wizard.GONet_utils.src.extractors.file_info import FileInfo
from GONet_Wizard.GONet_utils.src.extractors.time_info import TimeInfo
from GONet_Wizard.GONet_utils.src.extractors.astro_info import AstroInfo
from GONet_Wizard.GONet_utils.src.extractors.weather_info import WeatherInfo
from GONet_Wizard.GONet_utils.src.extractors.shape_info import ShapeInfo
from GONet_Wizard.GONet_utils.src.extractors.extraction_values import ExtractionValues
from GONet_Wizard.GONet_utils.src.extractors.merge import merge_extractor_into_data
from GONet_Wizard.GONet_utils.src.extractors.core import Extractor,sort_extractors
import numpy as np
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)

# List of all extractors
ALL_EXTRACTORS = [
    FileInfo(),
    TimeInfo(),
    AstroInfo(),
    WeatherInfo(),
    ShapeInfo(),
    ExtractionValues()
]

def extract_all(file_list: List[str], channels: List[str], extraction_params: Dict[str, Any], extractors: List[Extractor] = ALL_EXTRACTORS) -> List[Dict[str, Any]]:
    """
    Run the extraction pipeline and return one row dictionary per observation.

    Parameters
    ----------
    file_list : :class:`list` of :class:`str`
        Input GONet image files.  These paths are also used as the alignment key
        when merging per-file extractor outputs.
    channels : :class:`list` of :class:`str`
        Image channels to process, for example ``["red", "green", "blue"]``.
    extraction_params : :class:`dict`
        Shape and extraction settings passed to the pixel-statistics extractor.
        The dictionary must contain the shape fields required by
        :meth:`GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.from_dict`.
    extractors : :class:`list` of :class:`.Extractor`, optional
        Extractor instances to execute. Defaults to :data:`ALL_EXTRACTORS`.

    Returns
    -------
    :class:`list` of :class:`dict`
        JSON-serializable row dictionaries.  Each row corresponds to one file
        that survived all per-file extractor alignment steps.

    Notes
    -----
    Extractors that emit a ``"files"`` key are merged by filepath.  If two
    extractors return different file subsets, only the intersection is retained
    so that all per-file columns stay aligned.
    """

    raw = {
        "file_list": file_list,
        "channels": channels,
        "extraction_parameters": extraction_params
    }

    context: Dict[str, Any] = {}
    data: Dict[str, Any] = {}

    # Separate ExtractionValues from the rest of the extractors
    extraction_values_extractor = next((e for e in extractors if isinstance(e, ExtractionValues)), None)
    other_extractors = [e for e in extractors if not isinstance(e, ExtractionValues)]

    if extraction_values_extractor:
        # Run ExtractionValues in parallel using a separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            extraction_values_future = executor.submit(extraction_values_extractor.extract, raw, context)

            # Run the rest of the extractors sequentially
            for extractor in sort_extractors(other_extractors):
                results, context = extractor.extract(raw, context)
                logger.debug("Extractor %s completed.", extractor.__class__.__name__)
                merge_extractor_into_data(data, results)

            # Wait for ExtractionValues to complete and retrieve its results
            extraction_values_results, _ = extraction_values_future.result()
            merge_extractor_into_data(data, extraction_values_results)
    else:
        # Run all extractors sequentially if ExtractionValues is not present
        for extractor in sort_extractors(extractors):
            results, context = extractor.extract(raw, context)
            logger.debug("Extractor %s completed.", extractor.__class__.__name__)
            merge_extractor_into_data(data, results)

    # Transform the final data dictionary into a list of dictionaries
    # Ensure all keys with list values have the same length
    keys = list(data.keys())
    lengths = [len(data[key]) for key in keys if isinstance(data[key], (list, np.ndarray))]

    num_observations = lengths[0] if lengths else 0
    final_data = [{} for _ in range(num_observations)]

    # Remove the "files" key from the final output if it exists, since it's only used for alignment
    if "files" in data:
        del data["files"]

    for key, value in data.items():
        if isinstance(value, (list, np.ndarray)):
            # Distribute list/array values across the final dictionaries
            for i in range(num_observations):
                final_data[i][key] = convert_to_serializable(value[i])
        elif isinstance(value, (str, float)):
            # Distribute float values across all dictionaries
            for i in range(num_observations):
                final_data[i][key] = convert_to_serializable(value)
        else:
            raise ValueError(f"Unsupported data type for key '{key}': {type(value)}")

    return final_data


def convert_to_serializable(obj: Any) -> Any:
    """
    Convert numpy objects to standard Python types for JSON serialization.

    Parameters
    ----------
    obj : :class:`Any`
        The object to convert.

    Returns
    -------
    :class:`Any`
        A JSON-serializable object.

    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert numpy arrays to lists
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)  # Convert numpy floats to Python floats
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)  # Convert numpy integers to Python integers
    elif isinstance(obj, np.str_):
        return str(obj)  # Convert numpy strings to Python strings
    else:
        return obj  # Return the object as is if it's already serializable
