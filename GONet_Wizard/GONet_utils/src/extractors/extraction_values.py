"""
Pixel extraction and photometric statistics
===========================================

This module defines the :class:`.ExtractionValues` extractor and supporting
functions for performing pixel-level aperture extractions on GONet image files.

It applies shape-defined masks (e.g., circles, annuli) to calibrated image
channels and computes pixel statistics such as total counts, mean, standard
deviation, and number of contributing pixels. The extractor runs in parallel
across files for efficiency and returns per-file, per-channel measurements
ready for downstream analysis or tabular export.

**Functions**

:func:`.extract_counts_from_region`
    Compute statistics for pixels selected by a mask.

:func:`.process_single_file`
    Process a single image file and extract pixel count statistics for specified regions.

**Classes**

:class:`.ExtractionValues`
    Performs pixel count extraction for specified regions in image files.
    
"""


from GONet_Wizard.GONet_utils.src.extractors.core import Extractor, extraction_output
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_utils import DATA_SPEC
from GONet_Wizard.GONet_utils.src.extract_app.shapes import base
from typing import Dict, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import numpy as np

class ExtractionValues(Extractor):
    """
    Performs pixel count extraction for specified regions in image files.

    This class inherits from the base :class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor`
    class and implements methods to extract pixel count statistics from specified regions in image files.

    Attributes
    ----------
    USES : :class:`list`
        A list of context keys required by this extractor. For `ExtractionValues`, this is empty
        as it operates directly on the raw input.
    PROVIDES : :class:`list`
        A list of keys that this extractor provides to the extraction pipeline. For `ExtractionValues`,
        this is empty as it only updates the shared context.

    """

    USES = []
    PROVIDES = []

    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract pixel count statistics for specified regions in image files.

        This method processes a list of image files using the specified channels and extraction
        parameters. For each file, it applies a mask defined by the shape parameters and computes
        statistics for the pixel values within the masked region.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. Must include:

            - `file_list` (:class:`list` of :class:`str`): List of file paths to process.
            - `channels` (:class:`list` of :class:`str`): List of channels to process for each file.
            - `extraction_parameters` (:class:`dict`): Parameters for the extraction process, including
              shape definitions and other relevant settings.

        context : :class:`dict`
            A shared dictionary for intermediate results. This extractor does not modify the context.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with extracted pixel count statistics for each file and channel, including:
            - `total_counts` (:class:`float`): Sum of pixel values within the masked region.
            - `mean_counts` (:class:`float`): Average of the pixel values within the masked region.
            - `std` (:class:`float`): Standard deviation of the pixel values within the masked region.
            - `npixels` (:class:`int`): Number of pixels within the masked region.
            - The unchanged `context` dictionary.

        Raises
        ------
        :class:`ValueError`
            If the `file_list`, `channels`, or `extraction_parameters` keys are missing or invalid in the raw input.

        Notes
        -----
        - The `extraction_parameters` dictionary must include a `shape` key specifying the type of shape.
        - The :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` framework is used to dynamically instantiate the appropriate shape subclass and generate
          masks for pixel count extraction.
        - The method uses multiprocessing to process files in parallel for improved performance.

        """
        night_data = []
        with ProcessPoolExecutor(max_workers=12) as executor:
            # Submit tasks directly with all arguments
            futures = [executor.submit(process_single_file, file, raw["channels"], raw["extraction_parameters"]) for file in raw["file_list"]]

            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing:"):
                result = future.result()
                if result is not None:
                    night_data.append(result)


        results = {
            "files": [],
            DATA_SPEC["exptime"].key: []
        }
        results.update({channel: [] for channel in raw["channels"]})
    
        for data in night_data:
            for key, values in data.items():
                results[key].append(values)

        return results, context


def extract_counts_from_region(data: np.ndarray | list, mask: np.ndarray) -> extraction_output:
    """
    Compute statistics for pixels selected by a mask.

    Parameters
    ----------
    data : :class:`numpy.ndarray` or :class:`list`
        2D image array.

    mask : :class:`numpy.ndarray`
        Boolean array of the same shape as `data` indicating which pixels to include.

    Returns
    -------
    :class:`.extraction_output`
        Statistical summary of pixel values in the masked region.

    """
    values = np.array(data)[mask]
    return extraction_output(
        total_counts = np.sum(values),
        mean_counts = np.mean(values),
        std = np.std(values),
        npixels = values.size
    )


def process_single_file(gonet_file: str, channels: list, extraction_params: dict) -> dict:
    """
    Process a single image file and extract pixel count statistics for specified regions.

    This method applies a mask defined by the shape parameters to the GONet image file
    (loaded as a :class:`~GONet_Wizard.GONet_utils.GONetFile` object) and computes
    statistics for the pixel values within the masked region. The results are organized by
    image channels.

    Parameters
    ----------
    gonet_file : :class:`str`
        Path to the image file to process.
    channels : :class:`list` of :class:`str`
        List of channels to process for the image file (e.g., "red", "green", "blue").
    extraction_params : :class:`dict`
        Parameters for the extraction process, including shape definitions and other relevant settings.

    Returns
    -------
    :class:`dict`
        A dictionary containing pixel count statistics for each channel. Each channel key maps to:

        - `total_counts` (:class:`float`): Sum of pixel values within the masked region.
        - `mean_counts` (:class:`float`): Average of the pixel values within the masked region.
        - `std` (:class:`float`): Standard deviation of the pixel values within the masked region.
        - `npixels` (:class:`int`): Number of pixels within the masked region.

    Notes
    -----
    - The `extraction_params` dictionary must include a `shape` key specifying the type of shape.
    - The :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` framework is used to dynamically instantiate the appropriate shape subclass and generate
        masks for pixel count extraction.
    - The image file is processed for each channel, and overscan regions are removed before applying the mask.

    """
    file_data = {}

    shape = base.Shape.from_dict(extraction_params)

    try:
        gof = GONetFile.from_file(gonet_file)
        gof.remove_overscan()
    except Exception as e:
        tqdm.write(f"\n[WARN] Skipping file due to error: {gonet_file}\n  → {e}")
        return None

    if gof.meta is not None:
        exptime = gof.meta.get("exposure_time", None)
    else:
        exptime = None

    file_data["files"] = gonet_file
    file_data[DATA_SPEC["exptime"].key] = exptime

    for ext in channels:
        img = gof.get_channel(ext)
        mask = shape.mask(img)
        ext_results = extract_counts_from_region(img, mask)
        file_data[ext] = {
            DATA_SPEC["total_counts"].key: ext_results.total_counts,
            DATA_SPEC["mean_counts"].key: ext_results.mean_counts,
            DATA_SPEC["std"].key: ext_results.std,
            DATA_SPEC["npixels"].key: ext_results.npixels
        }

    del gof
    return file_data