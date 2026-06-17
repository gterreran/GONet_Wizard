# GONet_Wizard/commands/ui_bridge.py

"""
CLI-to-UI Result Bridging Utilities
===================================

This module defines a small result protocol that allows CLI command handlers to
optionally request UI behavior (publishing HTML previews and opening/focusing
windows) without hard-coupling command modules to UI implementation details.

Command handlers may return legacy HTML strings (backward compatible) or structured
request objects. Results are normalized and then realized by publishing preview
content to the unified UI server and/or ensuring a window exists via the window
manager. If windows are requested, the webview event loop is started.

Classes
-------
:class:`PublishRequest`
    Request to publish an HTML document into the preview manager under a channel.
:class:`WindowRequest`
    Request to open/focus a window under a stable key, optionally publishing
    preview HTML first.

Functions
---------
:func:`realize_ui_result`
    Normalize and apply UI result(s), returning whether a window was requested.
:func:`maybe_present_ui_result`
    Apply UI result(s) and start the webview loop if needed.
:func:`wrap_handler_for_ui`
    Wrap a command ``cli_handler`` so it can return UI results and be handled
    consistently from the CLI.

"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, List, Optional, Union


@dataclass
class PublishRequest:
    """
    Request to publish HTML into the PreviewManager under a channel.

    Attributes
    ----------
    channel : :class:`str`
        Preview channel name.
    html : :class:`str`
        Full HTML document (e.g. Plotly ``fig.to_html(full_html=True)`` output).
    title : :class:`str`, optional
        Preview title stored for the channel.
    """
    channel: str
    html: str
    title: Optional[str] = None


@dataclass
class WindowRequest:
    """
    Request to open/focus a window under a stable key.

    A window request may optionally include a :class:`.PublishRequest`, allowing
    preview content to be published before the window is shown.

    Attributes
    ----------
    key : :class:`str`
        Window identity key used by the window manager registry.
    spec : :class:`~GONet_Wizard.ui.windows.WindowSpec`
        Window specification (title/url/size).
    publish : :class:`.PublishRequest`, optional
        If provided, publish preview HTML before opening/focusing the window.
    """
    key: str
    spec: Any  # WindowSpec (imported lazily by caller or in normalization)
    publish: Optional[PublishRequest] = None


UIResult = Union[
    None,
    str,  # backward-compatible: HTML preview for cmd_name
    WindowRequest,
    PublishRequest,  # publish only, no window
    List[Any],
    tuple,
]


def _default_title_from_channel(channel: str) -> str:
    """
    Build a human-readable window title from a preview channel name.

    Parameters
    ----------
    channel : :class:`str`
        Preview channel identifier.

    Returns
    -------
    :class:`str`
        Title-cased string derived from the channel name, falling back to
        ``"Preview"`` if the channel is empty.
    """
    return channel.replace("_", " ").strip().title() or "Preview"


def _publish_html(req: PublishRequest) -> None:
    """
    Publish preview HTML to the unified preview manager.

    Parameters
    ----------
    req : :class:`.PublishRequest`
        Publish request containing the channel name and full HTML document.

    Returns
    -------
    None
    """
    from GONet_Wizard.ui import preview_manager
    preview_manager.publish_html(req.channel, req.html, title=req.title)


def _ensure_window(req: WindowRequest) -> None:
    """
    Ensure a window exists (or is focused) for a given window request.

    Parameters
    ----------
    req : :class:`.WindowRequest`
        Window request containing the registry key and window specification.

    Returns
    -------
    None
    """
    from GONet_Wizard.ui import WINDOWS
    WINDOWS.ensure(req.key, req.spec)


def _normalize_result(cmd_name: str, result: Any, *, port: int) -> UIResult:
    """
    Normalize a command handler return value into a UI result protocol.

    This function provides backward compatibility for commands that return a
    legacy HTML string by converting it into a :class:`.WindowRequest` that
    publishes the HTML under ``cmd_name`` and opens ``/view/<cmd_name>`` on the
    unified UI server.

    Parameters
    ----------
    cmd_name : :class:`str`
        Command name used as the default preview channel for legacy results.
    result : :class:`object`
        Value returned by a command handler.
    port : :class:`int`
        Port used to construct unified UI preview URLs for legacy results.

    Returns
    -------
    :class:`.UIResult`
        A normalized UI result representation, or ``None`` if the value is not
        recognized as a UI result.

    Notes
    -----
    Lists and tuples are returned unchanged to support commands that emit
    multiple UI results.
    """
    if result is None:
        return None

    if isinstance(result, (list, tuple)):
        return result

    if isinstance(result, str):
        # Convert legacy HTML string into a WindowRequest that publishes then opens.
        from GONet_Wizard.ui.windows import WindowSpec

        channel = cmd_name
        title = _default_title_from_channel(channel)
        url = f"http://127.0.0.1:{port}/view/{channel}"

        return WindowRequest(
            key=channel,
            publish=PublishRequest(channel=channel, html=result, title=title),
            spec=WindowSpec(
                title=title,
                url=url,
                width=1250,
                height=800,
            ),
        )

    if isinstance(result, PublishRequest):
        return result

    if isinstance(result, WindowRequest):
        return result

    return None


def realize_ui_result(cmd_name: str, result: Any, *, port: int) -> bool:
    """
    Apply UI result(s) and return whether any window was requested.

    This function normalizes a handler return value and then:
    - publishes preview HTML when requested
    - ensures windows exist (or are focused) when requested
    - starts the unified UI server only when needed for preview-backed windows

    Parameters
    ----------
    cmd_name : :class:`str`
        Command name used for legacy string results.
    result : :class:`object`
        Value returned by a command handler.
    port : :class:`int`
        Port for the unified UI server used by preview-backed windows.

    Returns
    -------
    :class:`bool`
        ``True`` if at least one :class:`.WindowRequest` was realized, otherwise
        ``False``.

    Raises
    ------
    :class:`RuntimeError`
        If the unified UI server cannot be started when required.
    """
    from GONet_Wizard.ui.runtime import ensure_server_running

    normalized = _normalize_result(cmd_name, result, port=port)
    if normalized is None:
        return False

    if isinstance(normalized, (list, tuple)):
        requested_any = False
        for r in normalized:
            requested_any |= realize_ui_result(cmd_name, r, port=port)
        return requested_any

    if isinstance(normalized, PublishRequest):
        _publish_html(normalized)
        return False

    if isinstance(normalized, WindowRequest):
        # A WindowRequest implies we're using the unified desktop UI runtime.
        # Keep the contract simple: always ensure the unified server is up.
        ensure_server_running(port=port)

        if normalized.publish is not None:
            _publish_html(normalized.publish)

        _ensure_window(normalized)
        return True

    return False


def maybe_present_ui_result(
    cmd_name: str,
    result: Any,
    *,
    port: int = 5050,
    debug_webview: bool = False,
) -> None:
    """
    Realize any UI result and start the webview loop if windows were requested.

    Parameters
    ----------
    cmd_name : :class:`str`
        Command name used for legacy string results.
    result : :class:`object`
        Value returned by a command handler.
    port : :class:`int`, optional
        Port for the unified UI server. Defaults to ``5050``.
    debug_webview : :class:`bool`, optional
        If ``True``, start the webview loop with debugging enabled.

    Returns
    -------
    None

    Raises
    ------
    :class:`RuntimeError`
        If UI realization requires starting the unified UI server and startup
        fails.
    """
    from GONet_Wizard.ui.runtime import start_webview_loop

    requested = realize_ui_result(cmd_name, result, port=port)
    if requested:
        start_webview_loop(debug_webview=debug_webview)


def wrap_handler_for_ui(cmd: Any):
    """
    Wrap a command handler so it can emit UI results from a CLI invocation.

    The returned function calls ``cmd.cli_handler`` and then interprets its return
    value using :func:`maybe_present_ui_result`. This allows commands to return:

    - ``None`` (no UI action)
    - :class:`str` (legacy HTML preview; channel = ``COMMAND.name``)
    - :class:`.PublishRequest` (publish only)
    - :class:`.WindowRequest` (open/focus a window, optional publish)
    - a :class:`list` or :class:`tuple` containing any mix of the above

    Parameters
    ----------
    cmd : :class:`object`
        Command module or object exposing a ``cli_handler`` callable and
        optionally a :data:`COMMAND` specification.

    Returns
    -------
    :class:`collections.abc.Callable`
        A handler compatible with :mod:`argparse` dispatch that accepts an
        :class:`argparse.Namespace` and performs any requested UI actions.

    Raises
    ------
    :class:`AttributeError`
        If ``cmd`` does not define ``cli_handler``.
    """
    cmd_name = getattr(getattr(cmd, "COMMAND", None), "name", None) or getattr(cmd, "__name__", "command")

    def _handler(args: argparse.Namespace) -> None:
        result = cmd.cli_handler(args)

        ui_port = getattr(args, "ui_port", 5050)
        debug_webview = getattr(args, "debug_webview", False)

        maybe_present_ui_result(
            cmd_name,
            result,
            port=ui_port,
            debug_webview=debug_webview,
        )

    return _handler
