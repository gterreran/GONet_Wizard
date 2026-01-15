"""
GONet Wizard Unified UI Runtime
===============================

This subpackage implements the shared *desktop UI runtime* used across GONet
Wizard to present interactive outputs in a consistent way, regardless of whether
a workflow is launched from the CLI or from the GUI launcher.

Scope and Motivation
--------------------

GONet Wizard commands historically behaved like traditional CLI utilities:
they parsed arguments, performed work, and printed results to stdout (or wrote
files). As the project expanded to include interactive tooling (Dash apps,
HTML previews, and a PyWebview-based desktop experience), a central requirement
emerged:

**The same command handler should be able to produce a terminal-only result or
a GUI-presented result without duplicating logic.**

This subpackage provides that bridge by defining a small set of primitives for:

- **hosting UI content** at stable local URLs (via a unified Flask server),
- **publishing "latest output" previews** under stable channel names, and
- **opening/focusing windows** in a controlled, process-safe way (via pywebview).

This allows command handlers to return structured UI intents (publish preview,
open window, or both) while keeping the handler itself independent of the window
backend and event-loop lifecycle.

Core Concepts
-------------

**Unified local server**
    A single Flask application hosts the GUI launcher pages and the preview
    endpoints. Any part of the application can rely on stable URLs such as
    ``/view/<channel>`` to display the most recent output for a given channel.

**Preview channels**
    Command outputs can be published under a channel name (often the command
    name, such as ``"show"``). The preview registry stores only the latest HTML
    for each channel, making it easy to re-run a command and refresh a window
    without creating new routes or templates.

**Window registry**
    Pywebview windows are managed through a key-based registry. A window can be
    "ensured" (created if missing, reused if already open), which prevents
    duplicate windows and supports workflows where repeated command execution
    should update an existing view.

**Event-loop discipline**
    Pywebview’s event loop must be started at most once per process. This
    subpackage includes runtime checks and launcher-mode signaling so that
    command handlers invoked *from inside* the GUI do not accidentally attempt to
    start a second event loop.

Module Layout
-------------

- :mod:`GONet_Wizard.ui.server`
  Creates and starts the unified Flask server used by the desktop runtime.

- :mod:`GONet_Wizard.ui.preview`
  Implements the preview registry and the Flask blueprint providing stable
  preview routes (shell + raw HTML views).

- :mod:`GONet_Wizard.ui.windows`
  Provides :class:`~GONet_Wizard.ui.windows.WindowSpec` and the process-wide
  window registry :data:`~GONet_Wizard.ui.windows.WINDOWS`.

- :mod:`GONet_Wizard.ui.runtime`
  Manages launcher-mode signaling and safe startup of the pywebview event loop,
  and exposes a stable API to ensure the unified server is running.

- :mod:`GONet_Wizard.ui.api`
  Defines :class:`~GONet_Wizard.ui.api.WebviewAPI`, the Python-side JavaScript
  bridge exposed to frontend pages as ``window.pywebview.api``.

- :mod:`GONet_Wizard.ui.dash_runner`
  Provides shared utilities for launching Dash servers in background threads and
  reusing running instances, enabling multiple Dash-based tools to share a
  consistent startup pattern.

Public API
----------

This package re-exports a small set of stable objects and helpers that are used
throughout GONet Wizard:

- :data:`WINDOWS` and :class:`WindowSpec` for window creation and management
- launcher-mode helpers (:func:`set_launcher_mode`, :func:`in_launcher_mode`)
- event-loop startup helper (:func:`start_event_loop_if_needed`)
- unified server helper (:func:`ensure_server_running`)
- :data:`preview_manager` for publishing preview content

"""

from .windows import WINDOWS, WindowSpec
from .runtime import (
    set_launcher_mode,
    in_launcher_mode,
    start_event_loop_if_needed,
    ensure_server_running,
)
from .preview import preview_manager

__all__ = [
    "WINDOWS",
    "WindowSpec",
    "set_launcher_mode",
    "in_launcher_mode",
    "start_event_loop_if_needed",
    "ensure_server_running",
    "preview_manager",
]
