UI Runtime
==========

The GONet Wizard UI runtime is the process-level infrastructure that hosts the
desktop graphical interface, preview windows, and Dash-based interactive tools.

This page describes how the runtime works internally. It complements
:doc:`GUI architecture developer notes <gui_architecture>`, which explains how GUI forms connect to the shared
command system.

The runtime is responsible for:

* Starting and reusing the local Flask server.
* Hosting launcher and command-form routes.
* Publishing command previews under stable URLs.
* Creating and reusing PyWebview windows.
* Starting the PyWebview event loop safely.
* Launching Dash applications in background threads.
* Connecting command return values to graphical windows.

Runtime Ownership Boundaries
----------------------------

The runtime layer owns presentation lifecycle, not scientific processing.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Layer
     - Owns
   * - Command handlers
     - Input normalization, orchestration, and deciding whether UI presentation is needed.
   * - UI bridge
     - Translating handler return values into preview publishes and window requests.
   * - Unified Flask server
     - Launcher routes, command forms, and preview routes.
   * - Window manager
     - PyWebview window creation, reuse, focusing, and cleanup.
   * - Dash runner
     - Dash app configuration, background server threads, and server reuse.

Feature code should request UI behavior through these layers rather than
starting servers or windows directly.

Runtime Components
------------------

The runtime is split across a small set of focused modules.

===================================== ==========================================
Module                                Responsibility
===================================== ==========================================
``ui/server.py``                      Unified local Flask server.
``gui/web.py``                        Launcher, command-form, and ``/run`` routes.
``ui/preview.py``                     HTML preview publishing and preview routes.
``ui/windows.py``                     ``WindowSpec`` and the window registry.
``ui/runtime.py``                     PyWebview event-loop and UI-mode guards.
``ui/api.py``                         Python API exposed to JavaScript.
``ui/dash_runner.py``                 Shared Dash application runner.
``ui/launch_forms.py``                Opens command forms from CLI parse errors.
``commands/ui_bridge.py``             Converts command results into UI actions.
===================================== ==========================================

The most important design principle is that commands do not directly manage the
desktop runtime. They return UI intents, and the runtime realizes those intents.


Runtime Entry Points
--------------------

The runtime is usually entered through one of these functions or return-value
objects:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Entry point
     - Used for
   * - ``ensure_server_running()``
     - Starting or reusing the unified local Flask server.
   * - ``WindowRequest``
     - Asking the UI bridge to open or focus a managed window.
   * - ``PublishRequest``
     - Publishing HTML preview content under a preview channel.
   * - ``WINDOWS.ensure(key, spec)``
     - Creating, reusing, or focusing a PyWebview window.
   * - ``start_webview_loop()``
     - Starting ``webview.start()`` at most once per process.
   * - ``ensure_dash_running()``
     - Starting or reusing a Dash server thread for an interactive app.

Commands should normally return ``WindowRequest`` or ``PublishRequest`` rather
than calling window or event-loop functions directly.

High-Level Runtime Flow
-----------------------

A typical window-backed command follows this path:

.. code-block:: text

   CLI or GUI form submission
        |
        v

   argparse parser
        |
        v

   wrapped command handler
        |
        v

   command cli_handler()
        |
        v

   UI result object
        |
        v

   commands/ui_bridge.py
        |
        +--> publish preview HTML
        |
        +--> ensure local Flask server
        |
        +--> ensure requested window
        |
        +--> start PyWebview event loop if needed

This flow allows the same command handler to be launched from the terminal or
from the GUI while keeping presentation concerns outside the scientific or
data-processing code.

Unified Flask Server
--------------------

The unified local server is implemented in ``ui/server.py``.

Its main entry points are:

* ``create_app()``
* ``ensure_server_running()``
* ``get_app()``
* ``get_server_port()``

``create_app()`` builds the Flask application and registers two important
blueprints:

* ``launcher_bp`` from ``gui/web.py``
* ``preview_bp`` from ``ui/preview.py``

The launcher blueprint serves the GUI homepage, command form pages, and the
``/run`` endpoint. The preview blueprint serves HTML previews at stable
``/view/<channel>`` URLs.

``ensure_server_running()`` starts the Flask app in a daemon thread if the
server is not already running. If the server is already active, the existing
port is reused.

The unified Flask server is intentionally local. It runs on ``127.0.0.1`` and
provides an internal HTTP surface for desktop windows and previews.

Launcher Routes
---------------

The GUI launcher routes are defined in ``gui/web.py`` through the
``launcher_bp`` Flask blueprint.

The main routes are:

==================== ==========================================================
Route                Purpose
==================== ==========================================================
``/``                Render the launcher homepage.
``/cmd/<cmd>``       Render a form page for one command.
``/run``             Execute a command from a GUI JSON payload.
==================== ==========================================================

The ``/run`` route is the bridge between HTML forms and the command system.

When a form is submitted:

#. The JSON payload is received by ``run_command()``.
#. ``get_cli_parser()`` lazily constructs the shared CLI parser.
#. ``payload_to_argv_with_parser()`` converts GUI fields into an
   argparse-compatible token list.
#. The parser creates the same ``argparse.Namespace`` used by the CLI.
#. ``args.handler(args)`` dispatches to the registered command handler.

This means the GUI does not maintain a separate command implementation.

Payload-to-argv Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~

``payload_to_argv_with_parser()`` is responsible for translating GUI form data
into command-line-style arguments.

For example, a form submission may become:

.. code-block:: text

   ["show", "file1.jpg", "file2.jpg", "--blue", "--green", "--red"]

The conversion uses argparse metadata to distinguish positional arguments from
optional flags. This is why form fields can remain closely aligned with command
specifications.

UI Result Protocol
------------------

The UI result protocol is implemented in ``commands/ui_bridge.py``.

Command handlers may return several kinds of values:

``None``
   No UI action is requested.

``str``
   Legacy HTML preview output.

``PublishRequest``
   Publish HTML under a preview channel without opening a window.

``WindowRequest``
   Open or focus a managed window.

``list`` or ``tuple``
   Multiple UI results.

``PublishRequest`` and ``WindowRequest`` allow commands to describe what they
want the UI to do without importing or controlling PyWebview directly.

The most important functions are:

``realize_ui_result()``
   Normalizes command output, publishes previews, ensures the Flask server is
   running when required, and creates or focuses requested windows.

``maybe_present_ui_result()``
   Calls ``realize_ui_result()`` and starts the PyWebview event loop if any
   windows were requested.

``wrap_handler_for_ui()``
   Wraps command ``cli_handler`` functions so they can transparently return UI
   result objects.

Parser Integration
------------------

Command handlers are wrapped during parser construction.

In ``commands/parser_builder.py``, ``register_simple_subcommand()`` attaches
handlers using ``wrap_handler_for_ui()``. As a result, both CLI invocations and
GUI form submissions pass through the same UI-aware dispatch wrapper.

This is why a command can return a ``WindowRequest`` regardless of whether it
was launched from:

* the terminal,
* the launcher,
* a command form,
* or parse-time routing to a form.

Preview System
--------------

HTML previews are implemented in ``ui/preview.py``.

The preview system has two main pieces:

``PreviewManager``
   A thread-safe in-memory registry mapping preview channels to the latest HTML
   output.

``preview_bp``
   A Flask blueprint exposing preview routes.

Preview content is published under a channel name, usually the command name.

For example:

.. code-block:: python

   preview_manager.publish_html("show", html, title="Show")

The preview routes are:

============================ ================================================
Route                        Purpose
============================ ================================================
``/view/<channel>``          Styled shell page for a preview channel.
``/view/<channel>/raw``      Raw published HTML with shared CSS injected.
============================ ================================================

This two-layer structure allows the shell page to remain stable while the raw
HTML for the channel changes after each command run.

Window Management
-----------------

Window management is centralized in ``ui/windows.py``.

The two key objects are:

``WindowSpec``
   Declarative description of a window, including title, URL, width, height,
   and whether it is resizable.

``WINDOWS``
   Process-wide ``WindowManager`` instance used throughout the package.

Windows are identified by stable keys such as:

* ``"launcher"``
* ``"show"``
* ``"show_meta"``
* ``"dashboard"``
* ``"extract-gui"``

The central method is ``WINDOWS.ensure(key, spec)``.

If a window with the requested key already exists, the existing window is
reused and the URL is refreshed on a best-effort basis. If no window exists, a
new PyWebview window is created.

Closed windows are removed from the registry by a watcher thread, allowing
future calls to recreate them cleanly.

Why Window Keys Matter
~~~~~~~~~~~~~~~~~~~~~~

Stable window keys prevent duplicate windows from accumulating when a user
runs the same command repeatedly.

For example, repeatedly launching image inspection should refresh or reuse the
``show`` window rather than creating a new unmanaged window each time.

PyWebview Event Loop
--------------------

PyWebview requires its event loop to be started carefully.

The event-loop guard is implemented in ``ui/runtime.py``.

The main functions are:

``start_webview_loop()``
   Start ``webview.start()`` at most once per process.

``start_event_loop_if_needed()``
   Backward-compatible wrapper around ``start_webview_loop()``.

``set_launcher_mode()``
   Mark the process as already running inside a launcher/webview context.

``in_launcher_mode()``
   Check whether launcher mode has been set.

``ensure_server_running()``
   Stable public wrapper around ``ui.server.ensure_server_running()``.

The runtime tracks whether ``webview.start()`` has already been called. If the
event loop is already running, subsequent calls return without starting a
second loop.

.. warning::

   New code should not call ``webview.start()`` directly.

   Commands should return ``WindowRequest`` objects or use the shared runtime
   helpers so that the event loop remains centralized and safe.

Launcher Command
----------------

The ``gui`` command is defined in ``commands/gui.py``.

Its ``cli_handler()`` performs two tasks:

#. Ensures the unified UI server is running.
#. Returns a ``WindowRequest`` for the launcher window.

The returned window request uses:

* key ``"launcher"``
* title ``"GONet Launcher"``
* URL ``http://127.0.0.1:<port>/``

The UI bridge then realizes the request and starts the PyWebview event loop if
needed.

Opening Command Forms from CLI Parse Errors
-------------------------------------------

The CLI can route some incomplete command invocations directly to GUI forms.

This behavior is implemented across:

* ``cli.py``
* ``ui/launch_forms.py``

In ``cli.py``, global UI flags such as ``--ui-port`` and
``--debug-webview`` are pre-parsed before the full command tree is parsed.

If parsing fails because a valid command was provided without required
arguments, and the invocation contains only command tokens, ``main()`` calls
``open_command_form()``.

``open_command_form()`` then:

#. Ensures the unified UI server is running.
#. Builds the ``/cmd/<command>`` URL.
#. Ensures the launcher window exists.
#. Starts the PyWebview event loop.

For example, a command-only invocation may open the corresponding GUI form
instead of only printing a terminal error.

Dash Application Runtime
------------------------

Dash applications are managed separately from the unified Flask server.

The shared Dash runner is implemented in ``ui/dash_runner.py``.

The key object is ``DashLaunchSpec``, which describes how to configure and
launch one Dash app. A launch spec provides:

* the Dash app instance,
* an ``app_key``,
* a configuration function,
* a layout function,
* a callback-registration function,
* and optionally an ``index_string`` function.

``ensure_dash_running()`` starts the Dash server in a background thread and
caches it by ``(app_key, port)``.

If the same app is requested again on the same port and the thread is alive,
the existing server is reused.

Dashboard Example
~~~~~~~~~~~~~~~~~

The dashboard command in ``commands/run_dashboard.py`` prepares input data,
calls ``ensure_dashboard_running()``, and returns a ``WindowRequest`` pointing
to the dashboard URL.

The UI bridge then opens or focuses the managed dashboard window.

Extraction GUI Example
~~~~~~~~~~~~~~~~~~~~~~

The interactive extraction GUI is launched through
``GONet_utils/src/extract_app/extract_gui.py``.

``ensure_extraction_gui_running()`` creates a ``DashLaunchSpec`` with
``app_key="extract-gui"`` and delegates server lifecycle management to
``ensure_dash_running()``.

This keeps the extraction GUI consistent with the dashboard launch pattern.

PyWebview JavaScript API
------------------------

The Python-side JavaScript bridge is implemented in ``ui/api.py`` as
``WebviewAPI``.

A ``WebviewAPI`` instance is attached to created PyWebview windows by the
window manager.

Frontend JavaScript can call this API through:

.. code-block:: javascript

   window.pywebview.api

The current API supports operations such as:

* opening native file-selection dialogs,
* opening native folder-selection dialogs,
* closing the active window,
* saving JSON data through a native dialog.

File and folder dialogs are guarded by a lock and debounced to avoid duplicate
dialogs from rapid clicks.

Adding a Runtime-Backed UI Feature
----------------------------------

When adding a new UI-backed feature, choose the integration pattern that
matches the output.

Static HTML Preview
~~~~~~~~~~~~~~~~~~~

Use this pattern when a command produces HTML output.

#. Let the command return an HTML string, or explicitly return a
   ``PublishRequest`` plus ``WindowRequest``.
#. Publish the content under a stable preview channel.
#. Open ``/view/<channel>`` in a managed window.

Interactive Dash App
~~~~~~~~~~~~~~~~~~~~

Use this pattern when the feature is a Dash app.

#. Define a ``DashLaunchSpec``.
#. Configure runtime inputs through the Dash server config or another explicit
   configuration function.
#. Register callbacks once through the launch spec.
#. Start or reuse the app with ``ensure_dash_running()``.
#. Return a ``WindowRequest`` pointing to the Dash URL.

Command Form
~~~~~~~~~~~~

Use this pattern when the feature is an ordinary command exposed through the
launcher.

#. Define or update the command specification.
#. Ensure arguments can be rendered by the GUI form.
#. Add or update the Jinja template when the generic form is not enough.
#. Let form submission flow through ``/run``.

Best Practices
--------------

Use ``WindowRequest`` instead of creating PyWebview windows directly.

Use stable window keys so repeated operations reuse windows.

Use ``DashLaunchSpec`` for Dash tools instead of hand-writing server launch
logic.

Keep command handlers independent of GUI state.

Keep the unified Flask server responsible for launcher and preview routes, and
keep Dash servers responsible for Dash applications.

Avoid calling ``webview.start()`` outside ``ui/runtime.py``.

Avoid storing long-lived scientific state in the window layer. Runtime state
should be limited to UI lifecycle concerns such as windows, preview HTML, and
server threads.

Relationship to Other Documentation
-----------------------------------

For the user-facing GUI guide, see :doc:`GUI Guide <../gui_guide/index>`.

For the architecture of GUI forms and command dispatch, see
:doc:`GUI architecture developer notes <gui_architecture>`.

For the command-line entry point and command parser behavior, see the API
reference for ``GONet_Wizard.cli`` and ``GONet_Wizard.commands``.

Summary
-------

The UI runtime lets GONet Wizard behave like a desktop application while still
preserving the command-oriented architecture of the package.

The key idea is that commands describe UI actions through structured return
values, while the runtime owns the concrete details of servers, windows,
previews, Dash apps, and the PyWebview event loop.
