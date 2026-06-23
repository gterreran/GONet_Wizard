"""
Filename metadata extractor
===========================

This module provides the :class:`.FileInfo` extractor, responsible for
deriving basic observational metadata directly from filenames. It parses
each filename to extract camera identifiers, Unix timestamps, and other
basic attributes required to initialize the extraction context.

The extractor serves as the first stage in the pipeline, establishing
the temporal reference for subsequent modules such as time, astronomy,
and weather extractors.

**Classes**

:class:`.FileInfo`
    Extracts metadata from filenames, such as camera ID and observation time.
"""

from GONet_Wizard.GONet_utils.src.extractors.core import Extractor
from GONet_Wizard.GONet_utils import DATA_SPEC
from astropy.time import Time
from typing import List, Dict, Any, Tuple
from pathlib import Path

class FileInfo(Extractor):
    """
    Extracts metadata from filenames.

    This class inherits from the base :class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor`
    class and is responsible for parsing filenames to extract relevant metadata
    such as camera ID and observation time.

    Attributes
    ----------
    USES : :class:`list`
        A list of dependencies required by this extractor. For `FileInfo`, this is empty
        as it operates directly on filenames.
    PROVIDES : :class:`list`
        A list of keys that this extractor provides to the extraction pipeline. For `FileInfo`,
        this includes "time" and other metadata keys.

    Notes
    -----
    - The filenames are expected to follow a specific format, such as: `cameraID_timestamp.extension`,
      where `cameraID` is an integer and `timestamp` is a Unix timestamp.

    """

    USES = []
    PROVIDES = ["time"]

    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract metadata from filenames and update the shared context.

        This method parses a list of filenames provided in the `raw` dictionary to extract
        metadata such as camera ID and observation time.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. Must include the key "file_list",
            which is a list of filenames to process.
        context : :class:`dict`
            A shared dictionary for intermediate results. This is updated with the extracted
            metadata, including observation times.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with extracted metadata, including:

              - `camera` (:class:`list` of int): Camera IDs extracted from filenames.
              - `unix_time` (:class:`list` of int): Unix timestamps extracted from filenames.
              - `filename` (:class:`list` of str): Original filenames.

            - The updated `context` dictionary, which includes:

              - `time` (:class:`astropy.time.Time`): Observation times converted to `astropy.Time`.

        Raises
        ------
        :class:`ValueError`
            If a filename does not follow the expected format.

        Notes
        -----
        - The filenames are expected to follow the format `cameraID_timestamp.extension`.
        - This method uses `astropy.time.Time` to convert Unix timestamps to time objects
          for further processing.

        """
        file_list: List[str] = raw["file_list"]

        # Use basenames for parsing camera/timestamp tokens, but preserve the
        # original path in the public ``filename`` output.  The dashboard uses
        # this full path to load image previews directly from extraction JSON
        # products without requiring a separate image-directory argument.
        basenames = [Path(f).name for f in file_list]
        filenames = [str(Path(f).expanduser()) for f in file_list]

        # Extract metadata from the basenames
        camera = [int(f.split('_')[0]) for f in basenames]
        unix_times = [int(f.split('_')[-1].split('.')[0]) for f in basenames]

        # Update the context with the time information
        context["time"] = Time(unix_times, format="unix")

        results = {
            "files": raw["file_list"],
            DATA_SPEC["filename"].key: filenames,
            DATA_SPEC["camera"].key: camera,
            DATA_SPEC["unix_time"].key: unix_times
        }

        return results, context