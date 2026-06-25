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

try:
    from dash_extensions.enrich import FileSystemBackend
except ImportError:  # pragma: no cover - compatibility with older dash-extensions
    try:
        from dash_extensions.enrich import FileSystemStore as FileSystemBackend
    except ImportError:  # pragma: no cover
        FileSystemBackend = None

import shutil, atexit, signal, os

import GONet_Wizard.settings as settings
from GONet_Wizard.logging_utils import get_logger
from GONet_Wizard.paths import cache_dir

logger = get_logger(__name__)

# Default filesystem backend folder used by dash-extensions when no backend
# is provided. Store it under the user cache directory instead of the package
# directory so frozen/installed applications never write into their install tree.
CACHE_DIR = cache_dir("dash", "extract_gui", "file_system_backend")
CACHE_DIRS = [CACHE_DIR]


def _serverside_output_transform() -> ServersideOutputTransform:
    """
    Build a server-side output transform using a user-writable cache directory.

    Returns
    -------
    dash_extensions.enrich.ServersideOutputTransform
        Transform configured to store temporary server-side callback payloads
        outside the package/install directory whenever the installed
        dash-extensions version exposes a filesystem backend class.
    """
    if FileSystemBackend is None:
        return ServersideOutputTransform()

    backend = FileSystemBackend(cache_dir=str(CACHE_DIR))

    try:
        return ServersideOutputTransform(backends=[backend])
    except TypeError:  # pragma: no cover - older dash-extensions API
        return ServersideOutputTransform(backend=backend)


def _clear_cache_dirs() -> None:
    """
    Reset the filesystem cache directories used by server-side Dash state.

    Each configured cache directory is removed, if present, and recreated. This
    prevents stale server-side objects from previous local runs from being
    reused by the extraction GUI.

    Returns
    -------
    None
    """
    for d in CACHE_DIRS:
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)

# Safety net: clear leftovers from previous run
_clear_cache_dirs()

# Flask + Dash app
server = Flask("GONet Wizard extraction GUI")
app = DashProxy(
    __name__,
    server=server,
    assets_folder=str(settings.STATIC),
    transforms=[_serverside_output_transform()],
)

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" type="image/x-icon" href="/assets/img/logo/GONet_Wizard.ico">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# --- Clean on process exit (and on SIGINT/SIGTERM) ---
def _on_exit(*_) -> None:
    """
    Clear extraction-GUI cache directories during interpreter or signal exit.

    Parameters
    ----------
    *_
        Optional positional arguments supplied by :mod:`atexit` or signal
        handlers. They are ignored.

    Returns
    -------
    None
    """
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