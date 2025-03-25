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