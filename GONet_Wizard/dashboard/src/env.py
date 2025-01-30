import datetime
from dateutil import tz

ROOT = '/Users/gterreran/Desktop/Work/data/GONet/AdlerRoof/'
ROOT_EXT = '/Volumes/Jackbackup/FarHorizons/data/GONet/AdlerRoof/'
CHANNELS = ['red', 'green', 'blue']
COLORS = {'red':lambda a: f'rgba(255,0,0,{a})', 'green':lambda a: f'rgba(0,128,0,{a})', 'blue':lambda a: f'rgba(0,0,255,{a})', 'gen':lambda a: f'rgba(0,0,0,{a})'}
CHICAGO_TZ = tz.gettz('America/Chicago')
DAY_START = datetime.datetime.strptime('12:00', '%H:%M').time()