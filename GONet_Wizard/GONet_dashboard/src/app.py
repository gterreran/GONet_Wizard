from .server import app
from .layout import layout

app.layout = layout

from . import callbacks
