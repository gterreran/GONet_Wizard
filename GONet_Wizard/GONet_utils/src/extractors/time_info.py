"""
Time metadata extractor
=======================

This module defines the :class:`.TimeInfo` extractor, responsible for deriving
comprehensive time-related metadata from an :class:`astropy.time.Time` object.

It converts raw observation timestamps into multiple temporal representations,
including UTC and local ISO-formatted datetimes, Modified Julian Date (MJD),
and both string and fractional time-of-day formats. The extractor also defines
a unique "night" tag used to group observations belonging to the same local night.

**Classes**

:class:`.TimeInfo`
    Extracts time-based information, including UTC and local timestamps, MJD, and time-of-day.
"""

from GONet_Wizard.GONet_utils.src.extractors.core import Extractor
from GONet_Wizard.GONet_utils import DATA_SPEC
from astropy.time import Time
from typing import Dict, Any, Tuple
from datetime import timezone
from GONet_Wizard.GONet_dashboard.src import env
import numpy as np

class TimeInfo(Extractor):
    """
    Extracts time-based information.

    This class inherits from the base :class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor`
    class and is responsible for processing time-related metadata from an
    :class:`astropy.time.Time` object provided in the shared context.

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
        local_tz = env.LOCAL_TZ

        # ---------- datetimes (vector) ----------
        # astropy -> tz-aware Python datetimes
        dt_utc = np.atleast_1d(time_list.to_datetime(timezone=timezone.utc))   # tz-aware UTC
        # ensure it's a 1-D object array even for length-1 inputs
        if getattr(dt_utc, "dtype", None) != object:
            dt_utc = np.array(dt_utc, dtype=object)

        dt_local = np.array([d.astimezone(local_tz) for d in dt_utc], dtype=object)

        # ---------- strings (ISO-8601, microseconds, with offsets) ----------
        date_utc   = np.array([d.isoformat(timespec="microseconds")  for d in dt_utc],   dtype=object)
        date_local = np.array([d.isoformat(timespec="microseconds")  for d in dt_local], dtype=object)

        # ---------- night tag (use local date; switch to UTC if you prefer) ----------
        night = dt_local[0].strftime("%Y%m%d")

        # ---------- MJD from astropy (vector) ----------
        mjd = time_list.mjd

        # ---------- seconds since midnight (UTC & local) ----------
        sm_utc = np.fromiter((d.hour*3600 + d.minute*60 + d.second for d in dt_utc),   dtype=int, count=len(dt_utc))
        sm_local = np.fromiter((d.hour*3600 + d.minute*60 + d.second for d in dt_local), dtype=int, count=len(dt_local))

        def format_hms(seconds: np.ndarray) -> np.ndarray:
            seconds = np.asarray(seconds, dtype=int)
            hh = seconds // 3600
            mm = (seconds % 3600) // 60
            ss = seconds % 60
            return (
                np.char.zfill(hh.astype(str), 2) + ":" +
                np.char.zfill(mm.astype(str), 2) + ":" +
                np.char.zfill(ss.astype(str), 2)
            )

        results = {
            "files": raw["file_list"],
            DATA_SPEC["night"].key: night,
            DATA_SPEC["date_utc"].key: date_utc,               # e.g. '2023-06-21T21:05:54.123456+00:00'
            DATA_SPEC["date_local"].key: date_local,           # e.g. '2023-06-21T16:05:54.123456-05:00'
            DATA_SPEC["mjd"].key: mjd,
            DATA_SPEC["hours_utc"].key: format_hms(sm_utc),
            DATA_SPEC["hours_local"].key: format_hms(sm_local),
            DATA_SPEC["float_hours_utc"].key: sm_utc / sec_per_day,     # fraction of day
            DATA_SPEC["float_hours_local"].key: sm_local / sec_per_day, # fraction of day
        }

        return results, context