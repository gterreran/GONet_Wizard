"""
Weather metadata extractor
==========================

This module defines the :class:`.WeatherInfo` extractor, responsible for retrieving
hourly meteorological conditions corresponding to each observation time.

It queries the local weather station defined in the environment configuration
and interpolates the closest hourly record for each observation. The extractor
provides standard meteorological fields such as temperature, dew point, humidity,
pressure, wind speed, and categorical condition codes.

**Classes**

:class:`.WeatherInfo`
    Fetches hourly weather conditions matched to observation times.
"""


from GONet_Wizard.GONet_utils.src.extractors.core import Extractor
from GONet_Wizard.GONet_utils import DATA_SPEC
from meteostat import Point, Hourly
from astropy.time import Time
from typing import Dict, Any, Tuple
import numpy as np
from datetime import timedelta
from GONet_Wizard.GONet_dashboard.src import env


class WeatherInfo(Extractor):
    """
    Fetches hourly weather conditions matched to each observation time.

    This class inherits from the base :class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor`
    class and is responsible for retrieving weather data such as temperature, humidity,
    wind speed, pressure, and condition codes for each observation time provided in the
    shared context.

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
        condition codes (see https://dev.meteostat.net/formats.html#weather-condition-codes).
        The data is matched to the closest hourly weather observation.

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
                "files": raw["file_list"],
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
            "files": raw["file_list"],
            DATA_SPEC["temperature"].key: temp[matched_indices],
            DATA_SPEC["dew_point"].key: dwpt[matched_indices],
            DATA_SPEC["wind_speed"].key: wspd[matched_indices],
            DATA_SPEC["pressure"].key: pres[matched_indices],
            DATA_SPEC["humidity"].key: rhum[matched_indices],
            DATA_SPEC["condition_code"].key: coco[matched_indices]
        }

        return results, context