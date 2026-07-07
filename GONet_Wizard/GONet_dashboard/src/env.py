"""
GONet Dashboard Configuration Environment.

This module defines constants and environment-specific settings shared across
the GONet Wizard dashboard. It includes plotting styles, default UI parameters,
geolocation metadata, timezone definitions, filtering thresholds, and other
common resources used throughout the dashboard and data processing utilities.

Constants
---------
CHANNELS : :class:`list` of :class:`str`
    Image channels used in processing and plotting (e.g., 'red', 'green', 'blue').

CHANNEL_COLORS : :class:`list` of :class:`str`
    Available color ratios between channels (e.g., 'green/blue').

BG_COLOR : :class:`str`
    Background color used across the dashboard and plot components.

TEXT_COLOR : :class:`str`
    Foreground text color used for UI elements and figure labels.

BASE_COLORS : :class:`dict`
    Dictionary mapping each channel to a base RGB color (without alpha).
    Used to generate RGBA strings via the `rgba()` function.

LOC_LAT : :class:`~astropy.units.Quantity`
    Latitude of the observing location (Adler roof) in degrees.

LOC_LON : :class:`~astropy.units.Quantity`
    Longitude of the observing location in degrees.

LOC_ALT : :class:`~astropy.units.Quantity`
    Altitude of the observing location in meters.

LOCAL_TZ : :class:`tzinfo`
    Timezone object for local time conversions (America/Chicago).

DAY_START_LOCAL : :class:`datetime.time`
    Local time used as the start of a "night" (used for grouping observations).

DAY_START_UTC : :class:`datetime.time`
    UTC equivalent of `DAY_START_LOCAL`.

DEFAULT_FILTER_VALUES : :class:`dict`
    Threshold defaults for interactive filtering components. Includes:
        - 'sunaltaz': minimum Sun altitude
        - 'moonaltaz': minimum Moon altitude
        - 'moon_illumination': maximum Moon illumination
        - 'condition_code': maximum weather condition index

OP : :class:`dict`
    Dictionary mapping string-based logical operators to Python equivalents.
    Supports basic comparison operations for filtering logic.

DEFAULT_OP : :class:`str`
    Default operator to apply during filter initialization (e.g., '<=').

Functions
---------
rgba(channel, alpha)
    Return a valid RGBA string for the given channel color and transparency.

Notes
-----
- This module is imported across layout, callbacks, and plotting utilities.
- The geolocation constants define the fixed position of the GONet camera system at Adler.
- Filtering logic and color styling are centralized here for consistent UI behavior.
"""
import datetime
import operator
from dateutil import tz
import astropy.units as u

CHANNELS = ['red', 'green', 'blue']

BG_COLOR = 'rgb(42, 42, 42)'
TEXT_COLOR = 'rgb(240, 240, 240)'
BASE_COLORS = {
    'red': [200, 60, 60],
    'green': [0, 150, 100],
    'blue': [60, 100, 200],
    'gen': [240, 240, 240]
}

def rgba(channel: str, alpha: float) -> str:
    """
    Return an RGBA string for the given channel name and alpha transparency.

    Parameters
    ----------
    channel : str
        One of the known color keys ('red', 'green', 'blue', 'gen').
    alpha : float
        The alpha value (0.0 to 1.0) for transparency.

    Returns
    -------
    str
        The rgba(...) string.
    """
    r, g, b = BASE_COLORS[channel]
    return f'rgba({r},{g},{b},{alpha})'

#Adler roof location
LOC_LAT = 41.86634580958955 * u.deg
LOC_LON = -87.60706566982965 * u.deg
LOC_ALT = (176+10) * u.m

LOCAL_TZ = tz.gettz('America/Chicago')
DAY_START_LOCAL = datetime.datetime.strptime('12:00', '%H:%M').time()
DAY_START_UTC = datetime.datetime.strptime('17:00', '%H:%M').time()

DEFAULT_FILTER_VALUES = {
    'sunaltaz': -18,
    'moonaltaz': 0,
    'moon_illumination': 0.2,
    'condition_code': 2,
}

OP = {
    '<': operator.lt ,
    '<=': operator.le ,
    '=': operator.eq ,
    '!=': operator.ne ,
    '=>': operator.ge ,
    '>': operator.gt ,
}

DEFAULT_OP = '<='

