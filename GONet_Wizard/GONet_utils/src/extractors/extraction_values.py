"""
Pixel extraction and masked-region statistics
=============================================

This module contains the extractor that performs the image-reading and
pixel-statistics portion of the extraction workflow.  Shape parameters are
converted into a :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape`,
which produces a boolean mask for each image channel.  The selected pixels are
then summarized with total counts, mean counts, standard deviation, and pixel
count.

The public :class:`.ExtractionValues` extractor processes many files in
parallel. Source-mode runs use a process pool by default, while frozen desktop
apps automatically use a thread pool because spawned process-pool workers are
fragile inside PyInstaller bundles. The lower-level :func:`.process_single_file`
helper performs the work for one image and is useful for testing or debugging
the extraction behavior on a single file.

Functions
---------
:func:`.extract_counts_from_region`
    Compute summary statistics for an image array and boolean mask.
:func:`.process_single_file`
    Open one GONet file, remove overscan, build a shape mask, and extract
    channel statistics.

Classes
-------
:class:`.ExtractionValues`
    Extractor implementation used by the pipeline runner.
"""


from GONet_Wizard.GONet_utils.src.extractors.core import Extractor, extraction_output
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_utils import DATA_SPEC
from GONet_Wizard.GONet_utils.src.extract_app.shapes import base
from typing import Dict, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from tqdm import tqdm
import os
import sys
import numpy as np

_EXECUTOR_ENV_VAR = "GONET_WIZARD_EXTRACT_EXECUTOR"
_DEFAULT_MAX_WORKERS = 12


def _running_in_frozen_app() -> bool:
    """
    Return whether the current process is running from a frozen desktop bundle.

    PyInstaller sets ``sys.frozen`` on bundled applications.  The extraction
    pipeline uses this to avoid spawning a nested process pool from the frozen
    GUI app, which can terminate worker processes abruptly on macOS and
    Windows.
    """
    return bool(getattr(sys, "frozen", False))


def _executor_mode() -> str:
    """
    Resolve the executor mode used for per-file pixel extraction.

    Returns
    -------
    :class:`str`
        One of ``"process"``, ``"thread"``, or ``"serial"``.

    Notes
    -----
    The optional ``GONET_WIZARD_EXTRACT_EXECUTOR`` environment variable can be
    set to ``process``, ``thread``, or ``serial`` for debugging.  Without an
    override, source-mode runs keep the existing process-pool behavior, while
    frozen desktop apps use threads to avoid PyInstaller multiprocessing worker
    crashes.
    """
    requested = os.environ.get(_EXECUTOR_ENV_VAR, "").strip().lower()
    if requested in {"process", "thread", "serial"}:
        return requested
    return "thread" if _running_in_frozen_app() else "process"


def _max_workers(n_files: int) -> int:
    """
    Return a bounded worker count for extraction parallelism.

    Parameters
    ----------
    n_files : :class:`int`
        Number of files submitted to the extractor.

    Returns
    -------
    :class:`int`
        At least one worker and at most :data:`_DEFAULT_MAX_WORKERS`, capped by
        the number of files.
    """
    return max(1, min(_DEFAULT_MAX_WORKERS, n_files or 1))


def _extract_files(
    file_list: list,
    channels: list,
    extraction_params: dict,
) -> list:
    """
    Process all files using the executor mode appropriate for this runtime.

    Parameters
    ----------
    file_list : :class:`list`
        Paths to the image files to process.
    channels : :class:`list`
        Channel names to extract.
    extraction_params : :class:`dict`
        Shape/extraction parameters passed to :func:`.process_single_file`.

    Returns
    -------
    :class:`list`
        Successful per-file extraction dictionaries.  Files that fail to load
        or process are skipped by :func:`.process_single_file`.
    """
    if not file_list:
        return []

    mode = _executor_mode()
    night_data = []

    if mode == "serial":
        for file in tqdm(file_list, total=len(file_list), desc="Processing", ncols=100):
            result = process_single_file(file, channels, extraction_params)
            if result is not None:
                night_data.append(result)
        return night_data

    executor_class = ThreadPoolExecutor if mode == "thread" else ProcessPoolExecutor
    with executor_class(max_workers=_max_workers(len(file_list))) as executor:
        futures = [
            executor.submit(process_single_file, file, channels, extraction_params)
            for file in file_list
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Processing",
            ncols=100,
        ):
            result = future.result()
            if result is not None:
                night_data.append(result)

    return night_data


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
        Extract masked pixel statistics for all requested files and channels.

        Parameters
        ----------
        raw : :class:`dict`
            Pipeline input dictionary. Required keys are:

            ``"file_list"``
                List of GONet image paths.
            ``"channels"``
                Channel names to extract from each image.
            ``"extraction_parameters"``
                Shape parameters accepted by
                :meth:`GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.from_dict`.
        context : :class:`dict`
            Shared pipeline context. This extractor does not require or modify
            context entries.

        Returns
        -------
        :class:`tuple`
            ``(results, context)`` where ``results`` contains a ``"files"``
            list, exposure times, and one nested statistics dictionary per
            requested channel.  The returned ``context`` is unchanged.

        Notes
        -----
        Files that cannot be opened or processed are skipped by
        :func:`.process_single_file`.  Downstream merging uses the returned
        ``"files"`` list to keep surviving rows aligned with other extractors.
        """
        night_data = _extract_files(
            raw["file_list"],
            raw["channels"],
            raw["extraction_parameters"],
        )

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
    Process one image file and return channel statistics for one shape.

    Parameters
    ----------
    gonet_file : :class:`str`
        Path to the image file to process.
    channels : :class:`list` of :class:`str`
        Channel names to extract from the image.
    extraction_params : :class:`dict`
        Shape parameters accepted by
        :meth:`GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape.from_dict`.

    Returns
    -------
    :class:`dict` or :data:`None`
        Per-file result dictionary, or ``None`` if the file cannot be loaded or
        processed.  Successful results include the filepath, exposure time, and
        one statistics dictionary per channel.  Each channel dictionary contains
        ``total_counts``, ``mean_counts``, ``std``, and ``npixels`` fields.

    Notes
    -----
    The image is loaded with :meth:`GONetFile.from_file`, overscan is removed,
    and the same shape mask is applied independently to each requested channel.
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