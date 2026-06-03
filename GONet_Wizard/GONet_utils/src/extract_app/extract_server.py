"""
Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance
used by the GONet extraction GUI, and configures **server-side state** via
`dash-extensions <https://github.com/thedirtyfew/dash-extensions>`_.

This module initializes:

- a :class:`flask.Flask` backend server named ``GONet Wizard extraction GUI``,
- a :class:`dash_extensions.enrich.DashProxy` app with
  :class:`dash_extensions.enrich.ServersideOutputTransform` enabled, so large
  Python objects (e.g., NumPy arrays) can be kept **server-side** and never
  serialized to the browser,
- a filesystem cache directory ``file_system_backend/`` used by the default
  dash-extensions backend for storing server-side objects,
- **startup and exit cleanup** of that cache directory to prevent stale files
  and uncontrolled growth during local runs.

This app is intended for **local, single-user** use. Clearing the cache on
startup/exit is a simple way to avoid disk accumulation and stale objects when
users load new data repeatedly. If you later require persistence across runs or
multi-process deployments, consider a networked backend (e.g., Redis) and remove
the auto-cleanup.

Attributes
----------
server : :class:`flask.Flask`
    The Flask backend used by the Dash application.

app : :class:`dash_extensions.enrich.DashProxy`
    The Dash app instance configured with server-side output support.

"""

from flask import Flask
from dash_extensions.enrich import DashProxy, ServersideOutputTransform
from pathlib import Path
import shutil, atexit, signal, os

from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)

# Default FS backend folder used by dash-extensions when no backend is provided
# (created in the current working directory). We’ll clean it proactively.
CACHE_DIRS = [
    Path(__file__).resolve().parent / "file_system_backend",  # common case
    Path.cwd() / "file_system_backend",                       # safety if CWD differs
]

def _clear_cache_dirs() -> None:
    for d in CACHE_DIRS:
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)

# Safety net: clear leftovers from previous run
_clear_cache_dirs()

# Flask + Dash app
server = Flask("GONet Wizard extraction GUI")
app = DashProxy(__name__, server=server,
                transforms=[ServersideOutputTransform()])

# --- Clean on process exit (and on SIGINT/SIGTERM) ---
def _on_exit(*_):
    try:
        _clear_cache_dirs()
        logger.debug("Serverside cache cleared.")
    except Exception:
        logger.exception("Cache cleanup failed.")

atexit.register(_on_exit)
for _sig in ("SIGINT", "SIGTERM"):
    if hasattr(signal, _sig):
        try:
            signal.signal(getattr(signal, _sig), lambda *_: (_on_exit(), os._exit(0)))
        except Exception:
            pass