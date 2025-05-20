"""
GONet Dashboard Configuration Environment.

This module defines constants and environment-specific settings shared across
the GONet Wizard dashboard. It includes plotting styles, default UI parameters,
and display properties.

Constants
---------
CHANNELS : :class:`list` of :class:`str`
    Image channels used in processing and plotting (e.g., 'red', 'green', 'blue').
BG_COLOR : :class:`str`
    Background color used across the dashboard and plot components.
TEXT_COLOR : :class:`str`
    Foreground text color used for UI elements and figure labels.
COLORS : :class:`dict`
    Dictionary mapping each channel to an RGBA-generating function with configurable alpha.
LOCAL_TZ : :class:`tzinfo`
    Local timezone for converting timestamps (America/Chicago).
DAY_START : :class:`datetime.time`
    Starting time used to group nightly observations across local midnight.
DEFAULT_FILTER_VALUES : :class:`dict`
    Predefined defaults for the interactive filtering interface.
LABELS : :class:`dict`
    Dictionary storing metadata keys categorized as:
    
    - 'gen': General labels not tied to specific channels.
    - 'fit': Fit-specific labels associated with individual channels.

OP : :class:`dict`
    Dictionary mapping string operators (e.g., '<', '!=') to their Python equivalents.
DEFAULT_OP : :class:`str`
    Default operator from the `OP` dictionary.

Notes
-----
- This module is imported across layout, callbacks, and plotting utilities.
"""
import datetime, operator
from dateutil import tz

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

LOCAL_TZ = tz.gettz('America/Chicago')
DAY_START = datetime.datetime.strptime('12:00', '%H:%M').time()

DEFAULT_FILTER_VALUES = {
    'sunaltaz': -18,
    'moonaltaz': 0,
    'moon_illumination': 0.2,
    'condition_code': 2,
}

LABELS = {'gen':[], 'fit':[]}

OP = {
    '<': operator.lt ,
    '<=': operator.le ,
    '=': operator.eq ,
    '!=': operator.ne ,
    '=>': operator.ge ,
    '>': operator.gt ,
}

DEFAULT_OP = '<='

