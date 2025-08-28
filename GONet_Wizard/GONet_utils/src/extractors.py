"""
This module defines a flexible and extensible framework for extracting structured
information from raw observational input. Each `Extractor` subclass defines a set
of output fields and declares any shared context dependencies, allowing automatic
ordering and execution of extractors based on declared `USES` and `PROVIDES`.

The system supports shared intermediate results (e.g., :class:`astropy.time.Time` objects),
field aliasing for backward compatibility, and clean separation of concerns. Extractors
are designed to process metadata, time-based information, astronomical ephemerides,
weather data, and pixel count statistics.

**Attributes**

ALL_EXTRACTORS : :class:`list` of :class:`.Extractor`
    List of all available extractors in the module, ordered by their typical usage.

**Functions**

:func:`.sort_extractors`
    Topologically sort extractors based on their `USES` and `PROVIDES` dependencies.
:func:`.extract_all`
    Run all extractors in dependency order and collect extracted fields.
:func:`.convert_to_serializable`
    Convert numpy objects to standard Python types for JSON serialization.
:func:`.extract_counts_from_region`
    Compute statistics for pixels selected by a mask.

**Classes**

:class:`.extraction_output`
    Container for the results of a circular aperture extraction.
:class:`.Extractor`
    Base class for all extractors, supporting dependency declarations and extraction logic.
:class:`.FileInfo`
    Extracts metadata from filenames, such as camera ID and observation time.
:class:`.TimeInfo`
    Extracts time-based information, including UTC and local timestamps, MJD, and time-of-day.
:class:`.AstroInfo`
    Computes solar and lunar altitudes and moon illumination for observation times.
:class:`.WeatherInfo`
    Fetches hourly weather conditions matched to observation times.
:class:`.ShapeInfo`
    Extracts shape-specific parameters for pixel count extraction.
:class:`.ExtractionValues`
    Performs pixel count extraction for specified regions in image files.

"""

from typing import List, Dict, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_sun, get_body
import astroplan
from meteostat import Hourly, Point
from tqdm import tqdm

from GONet_Wizard.GONet_dashboard.src import env
import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from GONet_Wizard.GONet_utils.src.data_spec import DATA_SPEC


@dataclass
class extraction_output:
    """
    Container for the results of a circular aperture extraction.

    Attributes
    ----------
    total_counts : :class:`float`
        Sum of pixel values within the circular region.

    mean_counts : :class:`float`
        Average of the pixel values within the circle.

    std : :class:`float`
        Standard deviation of the pixel values.

    npixels : :class:`int`
        Number of pixels within the circular region.

    """
    total_counts: float
    mean_counts: float
    std: float
    npixels: int


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


class Extractor(ABC):
    """
    Base class for all extractors.

    The `Extractor` class provides a framework for defining modular components
    that extract structured information from raw input data and shared context.
    Subclasses must implement the `extract` method and define the `USES` and
    `PROVIDES` attributes to declare dependencies and outputs.

    Attributes
    ----------
    USES : :class:`list` of :class:`str`
        A list of context keys required by the extractor. These keys must be
        available in the shared context before the extractor runs.
    PROVIDES : :class:`list` of :class:`str`
        A list of context keys created or updated by the extractor. These keys
        are added to the shared context after the extractor runs.

    Notes
    -----
    - The `USES` and `PROVIDES` attributes are used to determine the execution
      order of extractors in a pipeline. Extractors are executed in dependency
      order, ensuring that required context keys are available before an extractor runs.
    - Subclasses should focus on extracting specific types of information, such as
      metadata, time-based data, astronomical data, weather data, or pixel statistics.
    - The `extract` method must return a tuple containing:

      - A dictionary of extracted fields.
      - The updated shared context.


    """
    USES: List[str] = []
    PROVIDES: List[str] = []

    @abstractmethod
    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Abstract method to extract structured information from raw input and shared context.

        Subclasses must implement this method to define the logic for extracting specific
        types of information. It processes the raw input and shared context, returning
        extracted fields and the updated context.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. The structure of this dictionary
            depends on the specific extractor.
        context : :class:`dict`
            A shared dictionary for intermediate results. This dictionary is updated
            with the keys defined in the `PROVIDES` attribute.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary of extracted fields.
            - The updated shared context.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        raise NotImplementedError


class FileInfo(Extractor):
    """
    Extracts metadata from filenames.

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

        # Extract only the filename (without the path) before splitting
        filenames = [Path(f).name for f in file_list]

        # Extract metadata from the filenames
        camera = [int(f.split('_')[0]) for f in filenames]
        unix_times = [int(f.split('_')[-1].split('.')[0]) for f in filenames]

        # Update the context with the time information
        context["time"] = Time(unix_times, format="unix")

        results = {
            DATA_SPEC["filename"].key: file_list,
            DATA_SPEC["camera"].key: camera,
            DATA_SPEC["unix_time"].key: unix_times
        }

        return results, context



class TimeInfo(Extractor):
    """
    Extracts time-based information.

    Attributes
    ----------
    USES : :class:`list`
        A list of context keys required by this extractor. For `TimeInfo`, this includes
        "time", which must be an :class:`astropy.time.Time` object.
    PROVIDES : :class:`list`
        A list of keys that this extractor provides to the extraction pipeline. For `TimeInfo`,
        this is empty as it only updates the shared context.

    """

    USES = ["time"]
    PROVIDES = []

    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract time-based metadata and update the shared context.

        This method processes an :class:`astropy.time.Time` object provided in the shared
        context to compute various time-related metadata, including UTC and local timestamps,
        Modified Julian Date (MJD), and time-of-day information.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. This extractor does not use the `raw`
            dictionary directly.
        context : :class:`dict`
            A shared dictionary for intermediate results. Must include the key "time",
            which is an :class:`astropy.time.Time` object.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with extracted time-based metadata, including:
            - `night` (:class:`str`): Night tag derived from the first observation time.
            - `date_utc` (:class:`numpy.ndarray` of :class:`str`): UTC timestamps in ISO format.
            - `date_local` (:class:`numpy.ndarray` of :class:`str`): Local timestamps in ISO format.
            - `mjd` (:class:`numpy.ndarray` of :class:`float`): Modified Julian Date.
            - `hours_utc` (:class:`numpy.ndarray` of :class:`str`): Time-of-day in UTC (HH:MM:SS).
            - `hours_local` (:class:`numpy.ndarray` of :class:`str`): Time-of-day in local time (HH:MM:SS).
            - `float_hours_utc` (:class:`numpy.ndarray` of :class:`float`): Time-of-day in UTC as a fraction of a day.
            - `float_hours_local` (:class:`numpy.ndarray` of :class:`float`): Time-of-day in local time as a fraction of a day.
            - The updated `context` dictionary.

        Raises
        ------
        :class:`ValueError`
            If the "time" key is missing or invalid in the context.

        Notes
        -----
        - The `time` key in the context must be an :class:`astropy.time.Time` object.
        - Time-of-day calculations are provided in both string (HH:MM:SS) and fractional formats.

        """
        time_list: Time = context["time"]
        sec_per_day = 86400

        # First night tag
        night = time_list[0].to_datetime().strftime("%Y%m%d")

        # UTC ISO strings
        date_utc = np.char.add(time_list.isot, "+00:00")

        # Convert astropy Time to UTC datetime64[ns]
        utc_ns = time_list.unix.astype("datetime64[s]").astype("datetime64[ns]")
        local_tz = env.LOCAL_TZ

        # Convert to local time using tz-aware conversion
        local_ns = np.array([
            datetime.fromtimestamp(dt.astype("int64") // 1_000_000_000, tz=timezone.utc)
            .astimezone(local_tz)
            .replace(tzinfo=None)
            for dt in utc_ns
        ], dtype="datetime64[ns]")

        # Convert datetime64 to string representation
        date_local = local_ns.astype(str)

        # MJD
        mjd = time_list.mjd

        # Time-of-day
        def seconds_since_midnight(arr):
            return (arr - arr.astype("datetime64[D]")).astype("timedelta64[s]").astype(int)

        sm_utc = seconds_since_midnight(utc_ns)
        sm_local = seconds_since_midnight(local_ns)

        def format_hms(seconds: np.ndarray) -> np.ndarray:
            return (
                np.char.zfill((seconds // 3600).astype(str), 2) + ":" +
                np.char.zfill(((seconds % 3600) // 60).astype(str), 2) + ":" +
                np.char.zfill((seconds % 60).astype(str), 2)
            )

        results = {
            DATA_SPEC["night"].key: night,
            DATA_SPEC["date_utc"].key: date_utc,
            DATA_SPEC["date_local"].key: date_local,
            DATA_SPEC["mjd"].key: mjd,
            DATA_SPEC["hours_utc"].key: format_hms(sm_utc),
            DATA_SPEC["hours_local"].key: format_hms(sm_local),
            DATA_SPEC["float_hours_utc"].key: sm_utc / sec_per_day,
            DATA_SPEC["float_hours_local"].key: sm_local / sec_per_day
        }

        return results, context


class AstroInfo(Extractor):
    """
    Computes solar and lunar altitudes and moon illumination.

    Attributes
    ----------
    USES : :class:`list`
        A list of context keys required by this extractor. For `AstroInfo`, this includes
        "time", which must be an :class:`astropy.time.Time` object.
    PROVIDES : :class:`list`
        A list of keys that this extractor provides to the extraction pipeline. For `AstroInfo`,
        this is empty as it only updates the shared context.

    """

    USES = ["time"]
    PROVIDES = []

    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract astronomical metadata.

        This method computes the altitude of the Sun and Moon, as well as the fraction
        of the Moon illuminated, for each observation time provided in the shared context.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. This extractor does not use the `raw`
            dictionary directly.
        context : :class:`dict`
            A shared dictionary for intermediate results. Must include the key "time",
            which is an :class:`astropy.time.Time` object.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with extracted astronomical metadata, including:
            - `sunaltaz` (:class:`numpy.ndarray` of :class:`float`): Altitude of the Sun in degrees.
            - `moonaltaz` (:class:`numpy.ndarray` of :class:`float`): Altitude of the Moon in degrees.
            - `moon_illumination` (:class:`numpy.ndarray` of :class:`float`): Fraction of the Moon illuminated.
            - The updated `context` dictionary.

        Raises
        ------
        :class:`ValueError`
            If the "time" key is missing or invalid in the context.

        Notes
        -----
        - The `time` key in the context must be an :class:`astropy.time.Time` object.

        """
        time_list: Time = context["time"]
        location = EarthLocation(lat=env.LOC_LAT, lon=env.LOC_LON, height=env.LOC_ALT)
        altaz = AltAz(obstime=time_list, location=location)
        sunaltaz = get_sun(time_list).transform_to(altaz).alt.deg
        moonaltaz = get_body("moon", time_list).transform_to(altaz).alt.deg
        moon_illum = astroplan.moon.moon_illumination(time_list)

        results = {
            DATA_SPEC["sunaltaz"].key: sunaltaz,
            DATA_SPEC["moonaltaz"].key: moonaltaz,
            DATA_SPEC["moon_illumination"].key: moon_illum
        }

        return results, context


class WeatherInfo(Extractor):
    """
    Fetches hourly weather conditions matched to each observation time.

    Attributes
    ----------
    USES : :class:`list`
        A list of context keys required by this extractor. For `WeatherInfo`, this includes
        "time", which must be an :class:`astropy.time.Time` object.
    PROVIDES : :class:`list`
        A list of keys that this extractor provides to the extraction pipeline. For `WeatherInfo`,
        this is empty as it only updates the shared context.

    """

    USES = ["time"]
    PROVIDES = []

    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract hourly weather data and update the shared context.

        This method retrieves weather data for each observation time provided in the shared
        context. The weather data includes temperature, humidity, wind speed, pressure, and
        condition codes. The data is matched to the closest hourly weather observation.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. This extractor does not use the `raw`
            dictionary directly.
        context : :class:`dict`
            A shared dictionary for intermediate results. Must include the key "time",
            which is an :class:`astropy.time.Time` object.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with extracted weather data, including:
            - `temperature` (:class:`numpy.ndarray` of :class:`float`): Temperature in degrees Celsius.
            - `dew_point` (:class:`numpy.ndarray` of :class:`float`): Dew point temperature in degrees Celsius.
            - `wind_speed` (:class:`numpy.ndarray` of :class:`float`): Wind speed in kilometers per hour.
            - `pressure` (:class:`numpy.ndarray` of :class:`float`): Atmospheric pressure in hectopascals (hPa).
            - `humidity` (:class:`numpy.ndarray` of :class:`float`): Relative humidity as a percentage.
            - `condition_code` (:class:`numpy.ndarray` of :class:`int`): Weather condition codes.
            - The updated `context` dictionary.

        Raises
        ------
        :class:`ValueError`
            If the "time" key is missing or invalid in the context.

        Notes
        -----
        - The `time` key in the context must be an :class:`astropy.time.Time` object.
        - Weather data is fetched using the `meteostat.Hourly` API.
        - If no weather data is available for the requested time range, the method returns
          arrays filled with `NaN` values.

        """
        time_list: Time = context["time"]
        times = time_list.to_datetime()

        location = Point(env.LOC_LAT.value, env.LOC_LON.value, 70)

        # Align start_time to the previous full hour and end_time to the next full hour
        start_time = times[0].replace(minute=0, second=0, microsecond=0)
        end_time = times[-1].replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        # Fetch weather data
        weather_data = Hourly(location, start_time, end_time).fetch()

        # Handle empty weather data
        if weather_data.empty:
            print("Warning: No weather data available for the requested time range.")
            results = {
                DATA_SPEC["temperature"].key: np.full(len(times), np.nan),
                DATA_SPEC["dew_point"].key: np.full(len(times), np.nan),
                DATA_SPEC["wind_speed"].key: np.full(len(times), np.nan),
                DATA_SPEC["pressure"].key: np.full(len(times), np.nan),
                DATA_SPEC["humidity"].key: np.full(len(times), np.nan),
                DATA_SPEC["condition_code"].key: np.full(len(times), np.nan)
            }
            return results, context

        # Convert weather_data index to a NumPy array of datetime64
        weather_times = np.array(weather_data.index, dtype="datetime64[s]")

        # Convert weather_data columns to NumPy arrays
        temp = weather_data["temp"].to_numpy(dtype=float)
        dwpt = weather_data["dwpt"].to_numpy(dtype=float)
        wspd = weather_data["wspd"].to_numpy(dtype=float)
        pres = weather_data["pres"].to_numpy(dtype=float)
        rhum = weather_data["rhum"].to_numpy(dtype=float)
        coco = weather_data["coco"].to_numpy(dtype=int)

        # Match observation times to the closest weather times
        matched_indices = np.searchsorted(weather_times, times, side="left")
        matched_indices = np.clip(matched_indices, 0, len(weather_times) - 1)

        # Extract matched weather data
        results = {
            DATA_SPEC["temperature"].key: temp[matched_indices],
            DATA_SPEC["dew_point"].key: dwpt[matched_indices],
            DATA_SPEC["wind_speed"].key: wspd[matched_indices],
            DATA_SPEC["pressure"].key: pres[matched_indices],
            DATA_SPEC["humidity"].key: rhum[matched_indices],
            DATA_SPEC["condition_code"].key: coco[matched_indices]
        }

        return results, context


class ShapeInfo(Extractor):
    """
    Extracts shape-specific parameters for pixel count extraction.

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

        results = shape.get_extractor_field()

        return results, context


class ExtractionValues(Extractor):
    """
    Performs pixel count extraction for specified regions in image files.

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

    @staticmethod
    def process_single_file(gonet_file, extensions: list, extraction_params: dict) -> dict:
        """
        Process a single image file and extract pixel count statistics for specified regions.

        This method applies a mask defined by the shape parameters to the image file and computes
        statistics for the pixel values within the masked region. The results are organized by
        image extensions.

        Parameters
        ----------
        gonet_file : :class:`str`
            Path to the image file to process.
        extensions : :class:`list` of :class:`str`
            List of extensions to process for the image file (e.g., "red", "green", "blue").
        extraction_params : :class:`dict`
            Parameters for the extraction process, including shape definitions and other relevant settings.

        Returns
        -------
        :class:`dict`
            A dictionary containing pixel count statistics for each extension. Each extension key maps to:

            - `total_counts` (:class:`float`): Sum of pixel values within the masked region.
            - `mean_counts` (:class:`float`): Average of the pixel values within the masked region.
            - `std` (:class:`float`): Standard deviation of the pixel values within the masked region.
            - `npixels` (:class:`int`): Number of pixels within the masked region.

        Notes
        -----
        - The `extraction_params` dictionary must include a `shape` key specifying the type of shape.
        - The :class:`~~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` framework is used to dynamically instantiate the appropriate shape subclass and generate
          masks for pixel count extraction.
        - The image file is processed for each extension, and overscan regions are removed before applying the mask.

        """
        file_data = {}

        shape = base.Shape.from_dict(extraction_params)

        gof = GONetFile.from_file(gonet_file)
        for ext in extensions:
            gof.remove_overscan()
            for ext in extensions:
                mask = shape.mask(gof.get_channel(ext))
                ext_results = extract_counts_from_region(gof.get_channel(ext), mask)
                file_data[ext] = {
                    DATA_SPEC["total_counts"].key: ext_results.total_counts,
                    DATA_SPEC["mean_counts"].key: ext_results.mean_counts,
                    DATA_SPEC["std"].key: ext_results.std,
                    DATA_SPEC["npixels"].key: ext_results.npixels
                }

        del gof
        return file_data


    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract pixel count statistics for specified regions in image files.

        This method processes a list of image files using the specified extensions and extraction
        parameters. For each file, it applies a mask defined by the shape parameters and computes
        statistics for the pixel values within the masked region.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. Must include:

            - `file_list` (:class:`list` of :class:`str`): List of file paths to process.
            - `extensions` (:class:`list` of :class:`str`): List of extensions to process for each file.
            - `extraction_parameters` (:class:`dict`): Parameters for the extraction process, including
              shape definitions and other relevant settings.

        context : :class:`dict`
            A shared dictionary for intermediate results. This extractor does not modify the context.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary with extracted pixel count statistics for each file and extension, including:
            - `total_counts` (:class:`float`): Sum of pixel values within the masked region.
            - `mean_counts` (:class:`float`): Average of the pixel values within the masked region.
            - `std` (:class:`float`): Standard deviation of the pixel values within the masked region.
            - `npixels` (:class:`int`): Number of pixels within the masked region.
            - The unchanged `context` dictionary.

        Raises
        ------
        :class:`ValueError`
            If the `file_list`, `extensions`, or `extraction_parameters` keys are missing or invalid in the raw input.

        Notes
        -----
        - The `extraction_parameters` dictionary must include a `shape` key specifying the type of shape.
        - The :class:`~~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` framework is used to dynamically instantiate the appropriate shape subclass and generate
          masks for pixel count extraction.
        - The method uses multiprocessing to process files in parallel for improved performance.

        """
        night_data = []
        with ProcessPoolExecutor(max_workers=12) as executor:
            # Submit tasks directly with all arguments
            futures = [executor.submit(self.process_single_file, file, raw["extensions"], raw["extraction_parameters"]) for file in raw["file_list"]]

            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing:"):
                result = future.result()
                if result is not None:
                    night_data.append(result)

        results = {ext: [] for ext in raw["extensions"]}
        for data in night_data:
            for ext, values in data.items():
                results[ext].append(values)

        return results, context

def sort_extractors(extractors: List[Extractor]) -> List[Extractor]:
    """
    Topologically sort extractors based on their USES/PROVIDES dependencies.

    Parameters
    ----------
    extractors : :class:`list` of :class:`Extractor`
        Extractor instances to order.

    Returns
    -------
    :class:`list` of :class:`Extractor`
        Ordered list that respects dependency requirements.

    Raises
    ------
    :class:`RuntimeError`
        If there is a circular or unsatisfiable dependency.

    """
    provided_context: Set[str] = set()
    ordered: List[Extractor] = []
    remaining: Set[Extractor] = set(extractors)

    while remaining:
        ready = [e for e in remaining if all(req in provided_context for req in e.USES)]
        if not ready:
            raise RuntimeError("Circular or unsatisfiable dependencies detected.")
        for e in ready:
            ordered.append(e)
            provided_context.update(e.PROVIDES)
            remaining.remove(e)

    return ordered


# List of all extractors
ALL_EXTRACTORS = [
    FileInfo(),
    TimeInfo(),
    AstroInfo(),
    WeatherInfo(),
    ShapeInfo(),
    ExtractionValues()
]

def extract_all(file_list: List[str], extensions: List[str], extraction_params: Dict[str, Any], extractors: List[Extractor] = ALL_EXTRACTORS) -> List[Dict[str, Any]]:
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
    extensions : :class:`list`
        List of extensions to process for each file.
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
        "extensions": extensions,
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
                print(f"Extractor {extractor.__class__.__name__} completed.")
                data.update(results)

            # Wait for ExtractionValues to complete and retrieve its results
            extraction_values_results, _ = extraction_values_future.result()
            data.update(extraction_values_results)
    else:
        # Run all extractors sequentially if ExtractionValues is not present
        for extractor in sort_extractors(extractors):
            results, context = extractor.extract(raw, context)
            print(f"Extractor {extractor.__class__.__name__} completed.")
            data.update(results)

    # Transform the final data dictionary into a list of dictionaries
    # Ensure all keys with list values have the same length
    keys = list(data.keys())
    lengths = [len(data[key]) for key in keys if isinstance(data[key], (list, np.ndarray))]
    if len(set(lengths)) > 1:
        raise ValueError("All extracted lists must have the same length.")

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
