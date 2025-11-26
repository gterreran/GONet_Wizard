"""
Astronomical metadata extractor
===============================

This module defines the :class:`.AstroInfo` extractor, which computes
basic astronomical parameters for each observation time.

Using the observer's geographic location, it determines the Sun and
Moon altitudes above the horizon and calculates the fractional lunar
illumination. These quantities are useful for evaluating sky brightness
conditions and contextualizing night-sky measurements.

**Classes**

:class:`.AstroInfo`
    Computes solar and lunar altitudes and moon illumination for observation times.
"""


from GONet_Wizard.GONet_utils.src.extractors.core import Extractor
from GONet_Wizard.GONet_utils import DATA_SPEC
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_sun, get_body
import astroplan.moon
from typing import Dict, Any, Tuple
from GONet_Wizard.GONet_dashboard.src import env

class AstroInfo(Extractor):
    """
    Computes solar and lunar altitudes and moon illumination.

    This class inherits from the base :class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor`
    class and is responsible for calculating astronomical metadata based on observation times.

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
            "files": raw["file_list"],
            DATA_SPEC["sunaltaz"].key: sunaltaz,
            DATA_SPEC["moonaltaz"].key: moonaltaz,
            DATA_SPEC["moon_illumination"].key: moon_illum
        }

        return results, context