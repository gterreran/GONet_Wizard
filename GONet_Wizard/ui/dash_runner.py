# GONet_Wizard/ui/dash_runner.py

"""
Shared Dash Server Launch Utilities
===================================

This module centralizes the common launch pattern used across multiple Dash apps
in GONet Wizard. It provides a small, reusable runner that can configure and
start a Dash server in a background thread and re-use an existing running server
for a given ``(app_key, port)`` pair.

The runner is built around a declarative :class:`.DashLaunchSpec` which supplies
the app-specific "bricks" required to start a Dash app:

- a configuration function (e.g., populate ``app.server.config``),
- a layout builder,
- a callback registration function, and
- an optional ``index_string`` override.

To avoid noisy console output in production-style runs, the module can suppress
Flask/Werkzeug/Dash startup banners and request logs when debug is disabled.

Classes
-------
:class:`DashLaunchSpec`
    Declarative specification describing how to configure and launch a Dash app.
:class:`._RunnerState`
    Internal record tracking a running server thread and port.

Functions
---------
:func:`ensure_dash_running`
    Ensure a Dash server is running for a given launch spec and return its URL.
:func:`wait_for_port`
    Block until a TCP port is accepting connections.

"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from dash import Dash

from GONet_Wizard.logging_utils import silence_noisy_loggers


# --------------------------
# Types
# --------------------------

ConfigureFn = Callable[[Dash], None]
RegisterCallbacksFn = Callable[[], None]
LayoutFn = Callable[[Dash], object]  # layout object (Dash accepts component tree)
IndexStringFn = Callable[[], str]


@dataclass(frozen=True)
class DashLaunchSpec:
    """
    Specification describing how to configure and launch a Dash app.

    A :class:`.DashLaunchSpec` provides the app instance and a set of callables
    that supply app-specific configuration, layout construction, and callback
    registration. The :attr:`app_key` is used to cache and re-use already-running
    servers.

    Attributes
    ----------
    app : :class:`dash.Dash`
        Dash app instance to run.
    app_key : :class:`str`
        Unique identifier for this app type (e.g., ``"dashboard"``,
        ``"extract-gui"``). Used to cache/reuse running threads.
    configure : :class:`collections.abc.Callable`
        Callable invoked before starting the server. Use this to populate
        ``app.server.config`` and apply any runtime settings.
    layout : :class:`collections.abc.Callable`
        Callable that returns the layout object assigned to ``app.layout``.
    register_callbacks : :class:`collections.abc.Callable`
        Callable invoked after the layout is assigned and before the server
        starts. Typical usage is importing a callbacks module for side effects.
    index_string : :class:`collections.abc.Callable`, optional
        Optional callable returning a full Dash ``index_string`` override.
    """

    app: Dash
    app_key: str
    configure: ConfigureFn
    layout: LayoutFn
    register_callbacks: RegisterCallbacksFn
    index_string: Optional[IndexStringFn] = None


@dataclass
class _RunnerState:
    """
    Internal runner state for a launched Dash server.

    Attributes
    ----------
    thread : :class:`threading.Thread`
        Background thread running the Dash server.
    port : :class:`int`
        Port bound by the server.
    """
    thread: threading.Thread
    port: int


# Global registry: (app_key, port) -> running thread
_RUNNERS: dict[tuple[str, int], _RunnerState] = {}


# --------------------------
# Internals
# --------------------------

def _suppress_startup_noise() -> None:
    """
    Suppress Flask/Werkzeug/Dash startup banners and request logs.

    Returns
    -------
    None

    Notes
    -----
    This is only applied when debug is disabled.
    """
    silence_noisy_loggers()
    try:
        import flask.cli  # type: ignore
        flask.cli.show_server_banner = lambda *args, **kwargs: None  # noqa: E731
    except Exception:
        # If Flask changes internals, don't break launching.
        pass


def _run_dash_server(spec: DashLaunchSpec, *, debug: bool, port: int) -> None:
    """
    Configure and run the Dash server (blocking).

    Parameters
    ----------
    spec : :class:`.DashLaunchSpec`
        Launch specification containing the app and its app-specific callables.
    debug : :class:`bool`
        Whether to run in Dash debug mode.
    port : :class:`int`
        Port to bind to on localhost.

    Returns
    -------
    None
    """
    if not debug:
        _suppress_startup_noise()

    spec.configure(spec.app)
    spec.app.layout = spec.layout(spec.app)

    if spec.index_string is not None:
        spec.app.index_string = spec.index_string()

    spec.register_callbacks()

    spec.app.run_server(port=port, debug=debug, use_reloader=False)


def wait_for_port(
    host: str,
    port: int,
    *,
    timeout: float = 10.0,
    poll_interval: float = 0.05,
) -> None:
    """
    Block until a TCP port is accepting connections.

    Parameters
    ----------
    host : :class:`str`
        Hostname or IP address (e.g. ``"127.0.0.1"``).
    port : :class:`int`
        TCP port number.
    timeout : :class:`float`, optional
        Maximum time to wait in seconds. Defaults to ``10.0``.
    poll_interval : :class:`float`, optional
        Time between connection attempts in seconds. Defaults to ``0.05``.

    Returns
    -------
    None

    Raises
    ------
    RuntimeError
        If the port does not open within ``timeout`` seconds.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(poll_interval)
            try:
                sock.connect((host, port))
                return
            except (ConnectionRefusedError, OSError):
                time.sleep(poll_interval)

    raise RuntimeError(
        f"Dash server did not open port {host}:{port} within {timeout:.1f}s"
    )


# --------------------------
# Public API
# --------------------------

def ensure_dash_running(
    spec: DashLaunchSpec,
    *,
    debug: bool,
    port: int = 8050,
) -> str:
    """
    Ensure a Dash server is running for the given spec and port, and return its URL.

    If a server is already running for ``(spec.app_key, port)``, it is reused.

    Parameters
    ----------
    spec : :class:`.DashLaunchSpec`
        Launch specification for the Dash app.
    debug : :class:`bool`
        Whether to run Dash in debug mode.
    port : :class:`int`, optional
        Port to bind to on localhost. Defaults to ``8050``.

    Returns
    -------
    :class:`str`
        Local URL for the running server (e.g., ``"http://127.0.0.1:8050"``).
    """
    key = (spec.app_key, port)

    existing = _RUNNERS.get(key)
    if existing is not None and existing.thread.is_alive():
        return f"http://127.0.0.1:{port}"

    t = threading.Thread(
        target=_run_dash_server,
        kwargs={"spec": spec, "debug": debug, "port": port},
        daemon=True,
    )
    t.start()

    _RUNNERS[key] = _RunnerState(thread=t, port=port)

    wait_for_port("127.0.0.1", port, timeout=10.0)

    return f"http://127.0.0.1:{port}"
