"""
GONet Dashboard Configuration Environment.

This module defines shared constants and environment-specific settings
used throughout the GONet Wizard dashboard. These include paths to data
directories, display settings, default filter thresholds, and plotting styles.

Environment Variables
---------------------
GONET_ROOT : str
    Path to the root directory containing GONet metadata JSON files.
GONET_ROOT_IMG : str
    Path to the directory containing raw image files for preview and extraction.

Constants
---------
ROOT : str
    Loaded from the GONET_ROOT environment variable.
ROOT_EXT : str
    Loaded from the GONET_ROOT_IMG environment variable.
CHANNELS : list of str
    RGB channels used in image processing and plotting.
BG_COLOR : str
    Background color for plots and dashboards.
TEXT_COLOR : str
    Default text color for UI and figure labels.
COLORS : dict of callable
    Dictionary mapping channels to RGBA color functions.
LOCAL_TZ : tzinfo
    Local timezone for timestamp localization (America/Chicago).
DAY_START : datetime.time
    The start of the "astronomical day" for grouping nighttime observations.
DEFAULT_FILTER_VALUES : dict
    Predefined default values for interactive filters in the UI.
LABELS : dict
    Empty label placeholders for future data categorization. Separated by
    'gen' (general) and 'fit' (fit-specific) keys.

Notes
-----
- Color definitions use opacity-aware RGBA strings for overlay plotting.
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