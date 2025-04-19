"""
GONet Dashboard Configuration Environment.

This module defines constants and environment-specific settings shared across
the GONet Wizard dashboard. It includes paths, plotting styles, default UI
parameters, and display properties.

Environment Variables
---------------------
GONET_ROOT : :class:`str`
    Path to the root directory containing nightly GONet JSON metadata files.
GONET_ROOT_IMG : :class:`str`
    Path to the directory containing raw image files for preview and extraction.

Constants
---------
ROOT : :class:`str`
    Loaded from the ``GONET_ROOT`` environment variable.
ROOT_EXT : :class:`str`
    Loaded from the ``GONET_ROOT_IMG`` environment variable.
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

Notes
-----
- This module is imported across layout, callbacks, and plotting utilities.
"""
import os,datetime
from dateutil import tz

ROOT = os.getenv('GONET_ROOT')#'/Users/gterreran/Desktop/Work/data/GONet/AdlerRoof/'
ROOT_EXT = os.getenv('GONET_ROOT_IMG')#'/Volumes/Jackbackup/FarHorizons/data/GONet/AdlerRoof/'
CHANNELS = ['red', 'green', 'blue']

BG_COLOR = 'rgb(42, 42, 42)'
TEXT_COLOR = 'rgb(240, 240, 240)'
COLORS = {'red':lambda a: f'rgba(200, 60, 60,{a})', 'green':lambda a: f'rgba(0, 150, 100,{a})', 'blue':lambda a: f'rgba(60, 100, 200,{a})', 'gen':lambda a: f'rgba(240,240,240,{a})'}

LOCAL_TZ = tz.gettz('America/Chicago')
DAY_START = datetime.datetime.strptime('12:00', '%H:%M').time()

DEFAULT_FILTER_VALUES = {
    'sunaltaz': -18,
    'moonaltaz': 0,
    'moon_illumination': 0.2,
    'condition_code': 2,
}

LABELS = {'gen':[], 'fit':[]}