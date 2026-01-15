# GONet_Wizard/ui/preview.py

"""
Preview Publishing and Viewing for the Unified UI Server
========================================================

This module implements the preview subsystem used by GONet Wizard commands to
publish renderable HTML output and view it through the unified local UI server.
It provides:

- a thread-safe in-memory registry mapping preview channels to their latest HTML,
- a small Flask :class:`~flask.Blueprint` exposing routes to display previews, and
- a consistent HTML wrapper that injects shared UI styling.

Previews are keyed by a channel name (typically a command name such as
``"show"``), allowing command handlers to update the content for a known view
without managing windows or templates directly.

Classes
-------
:class:`PreviewPayload`
    Container for the latest HTML and title associated with a preview channel.
:class:`PreviewManager`
    Thread-safe registry for publishing and retrieving preview payloads.

Constants
---------
:data:`preview_manager`
    Singleton :class:`.PreviewManager` used across the UI layer.
:data:`preview_bp`
    Flask :class:`~flask.Blueprint` that registers preview routes.

Functions
---------
:func:`view_shell`
    Render a styled shell page that embeds a preview channel via an iframe.
:func:`view_raw`
    Return the raw HTML document for a preview channel with shared CSS injected.

"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional

from flask import Blueprint, Response, render_template, request


@dataclass
class PreviewPayload:
    """
    Payload containing the latest renderable output for a preview channel.

    Attributes
    ----------
    title : :class:`str`
        Human-readable title for the preview view.
    html : :class:`str`, optional
        Latest HTML content published for the channel. May be ``None`` if no
        content has been published yet.
    """
    title: str
    html: Optional[str] = None


class PreviewManager:
    """
    Thread-safe registry of preview outputs keyed by channel name.

    Preview content is stored in-memory and intended for local interactive use.
    Typical usage publishes HTML output under a stable channel name:

    ``preview_manager.publish_html("show", html, title="Show")``

    Attributes
    ----------
    _lock : :class:`threading.Lock`
        Mutex protecting registry operations.
    _data : :class:`dict`
        Mapping of channel name to :class:`.PreviewPayload`.
    """

    def __init__(self) -> None:
        """
        Initialize an empty preview registry.

        Returns
        -------
        None
        """
        self._lock = Lock()
        self._data: Dict[str, PreviewPayload] = {}

    def publish_html(self, channel: str, html: str, *, title: Optional[str] = None) -> None:
        """
        Publish HTML for a preview channel.

        If the channel does not exist, it is created. If it exists, the stored
        HTML is replaced, and the title is updated only when explicitly provided.

        Parameters
        ----------
        channel : :class:`str`
            Preview channel name.
        html : :class:`str`
            HTML content to publish for the channel.
        title : :class:`str`, optional
            Title to associate with the channel. If not provided for a new
            channel, a default title is constructed.

        Returns
        -------
        None
        """
        with self._lock:
            payload = self._data.get(channel)
            if payload is None:
                payload = PreviewPayload(title=title or f"Preview — {channel}", html=html)
                self._data[channel] = payload
                return

            payload.html = html
            if title is not None:
                payload.title = title

    def get(self, channel: str) -> PreviewPayload:
        """
        Retrieve the payload for a preview channel.

        If the channel does not exist, a placeholder payload is created and
        stored with no HTML content.

        Parameters
        ----------
        channel : :class:`str`
            Preview channel name.

        Returns
        -------
        :class:`.PreviewPayload`
            Payload for the requested channel.
        """
        with self._lock:
            payload = self._data.get(channel)
            if payload is None:
                payload = PreviewPayload(title=f"Preview — {channel}", html=None)
                self._data[channel] = payload
            return payload


preview_manager = PreviewManager()
preview_bp = Blueprint("preview", __name__)


@preview_bp.get("/view/<channel>")
def view_shell(channel: str):
    """
    Render the shell view for a preview channel.

    This route returns a styled page (template-driven) that embeds the raw HTML
    output for the channel, typically via an iframe pointed at
    ``/view/<channel>/raw``.

    Parameters
    ----------
    channel : :class:`str`
        Preview channel name.

    Returns
    -------
    :class:`str`
        Rendered HTML response for the shell template.
    """
    payload = preview_manager.get(channel)

    return render_template(
        "preview_shell.html",
        channel=channel,
        title=payload.title,
    )


@preview_bp.get("/view/<channel>/raw")
def view_raw(channel: str):
    """
    Return the raw HTML document for a preview channel.

    If no HTML has been published for the channel, a placeholder page is
    returned. Otherwise, the published HTML is wrapped in a minimal document
    that injects the shared stylesheet and disables caching to ensure reloads
    always reflect the latest published output.

    Parameters
    ----------
    channel : :class:`str`
        Preview channel name.

    Returns
    -------
    :class:`flask.Response`
        HTTP response containing an HTML document.
    """
    payload = preview_manager.get(channel)

    if not payload.html:
        return Response(
            "<h3>No output yet.</h3><p>Run a command to populate this view.</p>",
            mimetype="text/html",
        )

    html_doc = f"""<!doctype html>
    <html>
    <head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
    {payload.html}
    </body>
    </html>
    """

    resp = Response(html_doc, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp
