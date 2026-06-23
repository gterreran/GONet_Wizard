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

from queue import Empty, Queue
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
    startup_errors : :class:`queue.Queue`
        Queue used to report startup exceptions from the background thread to
        the caller waiting for the port to open.
    """

    thread: threading.Thread
    port: int
    startup_errors: Queue[BaseException]


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


def _raise_startup_error(
    startup_errors: Queue[BaseException] | None,
    *,
    app_key: str | None = None,
) -> None:
    """
    Raise the first queued Dash startup exception, if one is available.

    Parameters
    ----------
    startup_errors : :class:`queue.Queue` or None
        Queue populated by the Dash server thread when startup fails.
    app_key : :class:`str`, optional
        Human-readable app key included in the raised message.

    Returns
    -------
    None

    Raises
    ------
    RuntimeError
        If a startup exception has been reported by the background thread.
    """
    if startup_errors is None:
        return

    try:
        exc = startup_errors.get_nowait()
    except Empty:
        return

    label = f" {app_key!r}" if app_key else ""
    raise RuntimeError(f"Dash server{label} failed during startup: {exc}") from exc


def _run_dash_server(
    spec: DashLaunchSpec,
    *,
    debug: bool,
    port: int,
    startup_errors: Queue[BaseException] | None = None,
) -> None:
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
    startup_errors : :class:`queue.Queue`, optional
        Queue used to report exceptions to the launching thread while it waits
        for the server port to become available.

    Returns
    -------
    None
    """
    try:
        if not debug:
            _suppress_startup_noise()

        spec.configure(spec.app)
        spec.app.layout = spec.layout(spec.app)

        if spec.index_string is not None:
            spec.app.index_string = spec.index_string()

        spec.register_callbacks()

        spec.app.run_server(
            host="127.0.0.1",
            port=port,
            debug=debug,
            use_reloader=False,
        )
    except BaseException as exc:
        if startup_errors is not None:
            startup_errors.put(exc)
        raise


def wait_for_port(
    host: str,
    port: int,
    *,
    timeout: float = 30.0,
    poll_interval: float = 0.1,
    startup_errors: Queue[BaseException] | None = None,
    app_key: str | None = None,
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
        Maximum time to wait in seconds. Defaults to ``30.0``. Frozen desktop
        apps can take longer than source-mode runs to import, configure, and
        bind Dash apps.
    poll_interval : :class:`float`, optional
        Time between connection attempts in seconds. Defaults to ``0.1``.
    startup_errors : :class:`queue.Queue`, optional
        Queue populated by the background server thread if startup fails before
        the port opens.
    app_key : :class:`str`, optional
        App key included in startup error messages.

    Returns
    -------
    None

    Raises
    ------
    RuntimeError
        If the port does not open within ``timeout`` seconds, or if the Dash
        server reports a startup exception before the port opens.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        _raise_startup_error(startup_errors, app_key=app_key)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(poll_interval)
            try:
                sock.connect((host, port))
                return
            except (ConnectionRefusedError, OSError):
                time.sleep(poll_interval)

    _raise_startup_error(startup_errors, app_key=app_key)
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
    startup_timeout: float = 30.0,
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
    startup_timeout : :class:`float`, optional
        Maximum time to wait for the server port to open. Defaults to ``30.0``.

    Returns
    -------
    :class:`str`
        Local URL for the running server (e.g., ``"http://127.0.0.1:8050"``).

    Raises
    ------
    RuntimeError
        If the server fails during startup or does not open its port before the
        timeout expires.
    """
    key = (spec.app_key, port)

    existing = _RUNNERS.get(key)
    if existing is not None and existing.thread.is_alive():
        return f"http://127.0.0.1:{port}"

    startup_errors: Queue[BaseException] = Queue()

    t = threading.Thread(
        target=_run_dash_server,
        kwargs={
            "spec": spec,
            "debug": debug,
            "port": port,
            "startup_errors": startup_errors,
        },
        daemon=True,
    )
    t.start()

    _RUNNERS[key] = _RunnerState(
        thread=t,
        port=port,
        startup_errors=startup_errors,
    )

    try:
        wait_for_port(
            "127.0.0.1",
            port,
            timeout=startup_timeout,
            startup_errors=startup_errors,
            app_key=spec.app_key,
        )
    except RuntimeError:
        if not t.is_alive():
            _RUNNERS.pop(key, None)
        raise

    return f"http://127.0.0.1:{port}"
