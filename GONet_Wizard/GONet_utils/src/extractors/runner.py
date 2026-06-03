"""
Pipeline runner and public orchestration API
============================================

This module wires together the individual extractor modules into a single,
dependency-aware pipeline and exposes a stable entry point for batch
extraction.

Behavior
--------
- Define the canonical list of extractors (:data:`ALL_EXTRACTORS`) in their
  typical execution order.
- Orchestrate dependency resolution and execution via
  :func:`.extract_all`, invoking lightweight extractors sequentially and
  dispatching the heavy pixel-level extractor in parallel.
- Incrementally merge extractor outputs into a single accumulator using
  filepath-based alignment (inner join) to ensure all per-file arrays remain
  consistent even when some extractors drop files.


**Attributes**

ALL_EXTRACTORS : :class:`list` of :class:`.Extractor`
    List of all available extractors in the module, ordered by their typical usage.

**Functions**

:func:`.extract_all`
    Run all extractors in dependency order and collect extracted fields.

:func:`.convert_to_serializable`
    Convert numpy objects to standard Python types for JSON serialization.

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
    Run all extractors in dependency order and collect extracted fields.

    This function processes a list of extractors to extract structured information
    from raw observational input. Extractors are executed in dependency order, ensuring
    that required context keys are available before an extractor runs.

    If the `ExtractionValues` extractor is included in the list, it is executed in parallel
    with the other extractors, as it does not depend on their results. This parallelization
    improves performance by allowing `ExtractionValues` to process files concurrently while
    other extractors run sequentially.

    Parameters
    ----------
    file_list : :class:`list`
        List of file paths to process.
    channels : :class:`list`
        List of channels to process for each file.
    extraction_params : :class:`dict`
        Parameters for the extraction process.
    extractors : :class:`list` of :class:`.Extractor`, optional
        Extractor instances to run. Defaults to ``ALL_EXTRACTORS``.

    Returns
    -------
    :class:`list` of :class:`dict`
        A list of dictionaries, where each dictionary corresponds to an observation.

    Notes
    -----
    - Extractors are executed in dependency order based on their `USES` and `PROVIDES` attributes.
    - If `ExtractionValues` is included in the extractor list, it is executed in parallel
      using a separate thread, while the other extractors are executed sequentially.
    - If `ExtractionValues` is not included, all extractors are executed sequentially.
    - The final output is transformed into a list of dictionaries, where each dictionary
      corresponds to a single observation and contains the extracted fields.

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
