# GONet_Wizard/gui/web.py

"""
Flask Routes for the GONet Wizard GUI Forms
===========================================

This module defines the Flask blueprint powering the HTML form-based GUI used
by the GONet Wizard unified UI server. It serves:

- a landing page listing available commands,
- per-command form pages rendered from Jinja templates,
- a JSON endpoint that executes CLI commands from GUI-submitted payloads, and
- a streaming endpoint that emits live command feedback for GUI terminal panels.

The GUI is intentionally built on top of the existing CLI infrastructure. Form
submissions are converted into an ``argv`` list using argparse metadata, parsed
through the same command tree as the terminal CLI, and dispatched through the
registered command handler. This keeps the command logic centralized and avoids
duplicating behavior between CLI and GUI entry points.

To prevent circular import issues (commands importing UI helpers, while the UI
needs the command registry), the argparse parser is constructed lazily on first
use and cached for subsequent requests.

Constants
---------
:data:`launcher_bp` : :class:`flask.Blueprint`
    Flask blueprint registering the GUI routes.

Functions
---------
:func:`get_cli_parser`
    Lazily build and cache the CLI parser used to interpret GUI payloads.
:func:`index`
    Render the GUI landing page.
:func:`command_page`
    Render the form page for a specific command.
:func:`run_command`
    Execute a command using a GUI JSON payload and return captured feedback.
:func:`stream_command`
    Execute a command while streaming terminal-style feedback as server-sent events.
:func:`payload_to_argv_with_parser`
    Convert a GUI payload dictionary into an ``argv`` list using argparse metadata.

"""

from __future__ import annotations

import argparse
import json
import logging
import queue
import shlex
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Optional

from flask import Blueprint, Response, jsonify, render_template, request, stream_with_context

from GONet_Wizard import commands as commands_pkg
from GONet_Wizard.commands import cli_core
from GONet_Wizard.commands.argparse_errors import CliParseError
from GONet_Wizard.commands.smart_parser import SmartArgumentParser, set_current_argv
from GONet_Wizard.logging_utils import DEFAULT_LOG_FORMAT, PACKAGE_LOGGER_NAME


launcher_bp = Blueprint("launcher", __name__)
_COMMAND_RUN_LOCK = threading.Lock()


# ----------------------------
# Lazy CLI parser construction
# ----------------------------

_CLI_PARSER: Optional[argparse.ArgumentParser] = None


def get_cli_parser() -> argparse.ArgumentParser:
    """
    Lazily build and cache the CLI parser.

    Building the parser walks the command specification tree and imports command
    modules. This can trigger circular imports if done at module import time, so
    the parser is constructed on first use and cached.

    Returns
    -------
    :class:`argparse.ArgumentParser`
        CLI parser including all registered subcommands.
    """
    global _CLI_PARSER
    if _CLI_PARSER is None:
        parser = SmartArgumentParser(description="GONet Wizard command-line interface.")
        _CLI_PARSER = cli_core.build_subparser(parser, commands_pkg)
    return _CLI_PARSER


# ----------------------------
# Routes
# ----------------------------

@launcher_bp.get("/")
def index():
    """
    Render the GUI landing page.

    Returns
    -------
    :class:`str`
        Rendered HTML for the index page.
    """
    return render_template("index.html")


@launcher_bp.get("/cmd/<cmd>")
def command_page(cmd: str):
    """
    Render the form page for a specific command.

    Parameters
    ----------
    cmd : :class:`str`
        Command name token (e.g. ``"show"`` or ``"dashboard"``).

    Returns
    -------
    :class:`str`
        Rendered HTML for the command form page.
    """
    form_path = f"forms/{cmd}.html"
    try:
        return render_template("form_page.html", form_template=form_path, command_name=cmd)
    except Exception:
        return f"<p>Unknown command: {cmd}</p>"


@launcher_bp.post("/run")
def run_command():
    """
    Run a CLI command from a GUI JSON payload.

    The request payload is converted to an ``argv`` list using argparse metadata
    (positionals vs options), parsed through the shared CLI parser, and executed
    via ``args.handler(args)``.

    Returns
    -------
    :class:`flask.Response`
        JSON response describing success or error, optionally including an HTML
        output string when returned by the command handler.

    Raises
    ------
    RuntimeError
        If the parser cannot be constructed or command execution fails.
    """
    payload = request.get_json() or {}
    argv: list[str] = []

    try:
        parser = get_cli_parser()
        argv = payload_to_argv_with_parser(parser, dict(payload))  # copy
        if not argv:
            return jsonify({"status": "error", "message": "No command provided."})

        set_current_argv(argv)
        args = parser.parse_args(argv)

        if not hasattr(args, "handler"):
            return jsonify({"status": "error", "message": "No handler found for command."})

        result, terminal_output, error = _run_handler_with_terminal_capture(args, argv)

        if error is not None:
            return jsonify(
                {
                    "status": "error",
                    "message": str(error),
                    "argv": argv,
                    "terminal": terminal_output,
                }
            )

        resp = {
            "status": "success",
            "message": f"Executed: {' '.join(argv)}",
            "argv": argv,
            "terminal": terminal_output,
        }
        if isinstance(result, str) and result.strip():
            resp["output"] = result

        return jsonify(resp)

    except CliParseError as e:
        detail = (e.message or "").strip()
        message = (
            f"Invalid arguments: {detail}"
            if detail
            else "Invalid arguments. Please check your inputs."
        )
        return jsonify(
            {
                "status": "error",
                "message": message,
                "argv": argv,
                "terminal": _format_terminal_output(
                    argv,
                    status="error",
                    message=message,
                ),
            }
        )
    except SystemExit:
        message = "Invalid arguments. Please check your inputs."
        return jsonify(
            {
                "status": "error",
                "message": message,
                "argv": argv,
                "terminal": _format_terminal_output(argv, status="error", message=message),
            }
        )
    except Exception as e:
        message = str(e)
        return jsonify(
            {
                "status": "error",
                "message": message,
                "terminal": _format_terminal_output(
                    argv,
                    status="error",
                    message=message,
                    traceback_text="".join(
                        traceback.format_exception(type(e), e, e.__traceback__)
                    ),
                ),
            }
        )


@launcher_bp.post("/run/stream")
def stream_command():
    """Run a GUI command and stream live feedback as server-sent events.

    The regular ``/run`` route remains useful for simple JSON request/response
    workflows. This endpoint is optimized for the extraction form terminal panel:
    it validates the same GUI payload, runs the same command handler, and emits
    live terminal chunks as stdout, stderr, and package log messages are produced.

    Returns
    -------
    :class:`flask.Response`
        ``text/event-stream`` response containing ``status``, ``terminal``, and
        final ``done`` events.
    """
    payload = request.get_json() or {}
    response = Response(
        stream_with_context(_stream_command_events(dict(payload))),
        mimetype="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


def _request_named_window_close(key: str) -> None:
    """Best-effort close request for a registered pywebview window."""
    try:
        from GONet_Wizard.ui import WINDOWS

        threading.Timer(0.05, lambda: WINDOWS.close(key)).start()
    except Exception:
        return


@launcher_bp.post("/show/session/<session_id>/close")
def close_show_session(session_id: str):
    """Finalize a deferred interactive ``show`` session.

    The interactive show window explicitly calls this route when the user clicks
    ``Save figure`` or ``Exit``. The route immediately acknowledges the request
    and, when a save path is provided, performs the expensive figure rebuild and
    export in a background thread so the show window can close right away.

    Parameters
    ----------
    session_id : :class:`str`
        Identifier of the active show session.

    Returns
    -------
    :class:`flask.Response`
        JSON status describing whether the session was accepted.
    """
    from GONet_Wizard.commands.show.figure import build_show_figure
    from GONet_Wizard.commands.show.io import save_figure_plotly
    from GONet_Wizard.commands.show.session import show_session_registry

    session = show_session_registry.pop(session_id)
    if session is None:
        return jsonify({"status": "ignored", "message": "Session already closed."})

    payload = request.get_json(silent=True)
    if payload is None:
        raw = request.get_data(cache=False, as_text=True) or "{}"
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {}

    save_path = str(payload.get("save_path") or "").strip()
    terminal_stream = session.terminal_stream

    def _print_or_append(message: str) -> None:
        if terminal_stream is not None:
            terminal_stream.append(message)
        else:
            print(message, end="", flush=True)

    def _finish_success(message: str, output: str | None = None) -> None:
        if terminal_stream is not None:
            terminal_stream.finish(status="success", message=message, output=output)
        else:
            if output:
                print(f"SUCCESS: {message}\nOutput: {output}")
            else:
                print(f"SUCCESS: {message}")

    def _finish_error(message: str, exc: Exception) -> None:
        traceback_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if terminal_stream is not None:
            terminal_stream.finish(
                status="error",
                message=message,
                traceback_text=traceback_text,
            )
        else:
            print(f"ERROR: {message}")
            print(traceback_text)

    if not save_path:
        _finish_success("Show window closed without saving.")
        return jsonify({"status": "success", "message": "Show window closed."})

    def _background_save() -> None:
        stop_event = threading.Event()

        def _dot_worker() -> None:
            while not stop_event.wait(1.5):
                _print_or_append(".")

        dot_thread = threading.Thread(target=_dot_worker, daemon=True)
        try:
            _print_or_append(f"Saving show figure to {save_path}. Rebuilding figure in background")
            dot_thread.start()
            fig = build_show_figure(
                session.files,
                channels=session.channels,
                window_width_px=session.window_width_px,
                window_height_px=session.window_height_px,
                width_frac=0.90,
                row_height_frac=0.40,
            )
            output = save_figure_plotly(fig, str(save_path))
            stop_event.set()
            dot_thread.join(timeout=0.2)
            _finish_success("Show figure saved.", str(output))
        except Exception as exc:
            stop_event.set()
            dot_thread.join(timeout=0.2)
            _finish_error(f"Show save failed: {exc}", exc)

    threading.Thread(target=_background_save, daemon=True).start()
    return jsonify({"status": "success", "message": "Show save started.", "save_path": save_path})


@launcher_bp.post("/show_meta/session/<session_id>/close")
def close_show_meta_session(session_id: str):
    """Finalize an interactive ``show_meta`` session.

    The metadata preview calls this route when the user clicks ``Save PDF`` or
    ``Exit``. When a save path is provided, the PDF is written in a background
    worker while progress remains visible in the CLI or GUI terminal panel.

    Parameters
    ----------
    session_id : :class:`str`
        Identifier of the active metadata preview session.

    Returns
    -------
    :class:`flask.Response`
        JSON status describing whether the close/save request was accepted.
    """
    from GONet_Wizard.commands.show_meta import save_metadata_pdf
    from GONet_Wizard.commands.show_meta_session import show_meta_session_registry

    session = show_meta_session_registry.pop(session_id)
    if session is None:
        return jsonify({"status": "ignored", "message": "Session already closed."})

    _request_named_window_close("show_meta")

    payload = request.get_json(silent=True)
    if payload is None:
        raw = request.get_data(cache=False, as_text=True) or "{}"
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {}

    save_path = str(payload.get("save_path") or "").strip()
    terminal_stream = session.terminal_stream

    def _print_or_append(message: str) -> None:
        if terminal_stream is not None:
            terminal_stream.append(message)
        else:
            print(message, end="", flush=True)

    def _finish_success(message: str, output: str | None = None) -> None:
        if terminal_stream is not None:
            terminal_stream.finish(status="success", message=message, output=output)
        else:
            if output:
                print(f"SUCCESS: {message}\nOutput: {output}")
            else:
                print(f"SUCCESS: {message}")

    def _finish_error(message: str, exc: Exception) -> None:
        traceback_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if terminal_stream is not None:
            terminal_stream.finish(
                status="error",
                message=message,
                traceback_text=traceback_text,
            )
        else:
            print(f"ERROR: {message}")
            print(traceback_text)

    if not save_path:
        _finish_success("Show metadata window closed without saving.")
        return jsonify({"status": "success", "message": "Show metadata window closed."})

    def _background_save() -> None:
        stop_event = threading.Event()

        def _dot_worker() -> None:
            while not stop_event.wait(1.5):
                _print_or_append(".")

        dot_thread = threading.Thread(target=_dot_worker, daemon=True)
        try:
            _print_or_append(f"Saving metadata PDF to {save_path}")
            dot_thread.start()
            output = save_metadata_pdf(session.files, str(save_path))
            stop_event.set()
            dot_thread.join(timeout=0.2)
            _finish_success("Metadata PDF saved.", str(output))
        except Exception as exc:
            stop_event.set()
            dot_thread.join(timeout=0.2)
            _finish_error(f"Metadata PDF save failed: {exc}", exc)

    threading.Thread(target=_background_save, daemon=terminal_stream is not None).start()
    return jsonify({"status": "success", "message": "Metadata PDF save started.", "save_path": save_path})


# ----------------------------
# Command feedback capture
# ----------------------------

def _quote_argv(argv: list[str]) -> str:
    """
    Return a shell-like display string for a parsed argument vector.

    Parameters
    ----------
    argv : list of str
        Command tokens after GUI payload conversion.

    Returns
    -------
    str
        Display string prefixed with ``GONet_Wizard``.
    """
    if not argv:
        return "GONet_Wizard"
    return "GONet_Wizard " + shlex.join([str(token) for token in argv])


def _format_terminal_output(
    argv: list[str],
    *,
    status: str,
    message: str,
    logs: str = "",
    stdout: str = "",
    stderr: str = "",
    traceback_text: str = "",
) -> str:
    """
    Format captured command feedback for the GUI terminal panel.

    Parameters
    ----------
    argv : list of str
        Parsed command tokens shown at the top of the terminal panel.
    status : str
        Command status label, usually ``"success"`` or ``"error"``.
    message : str
        Human-readable summary line.
    logs : str, optional
        Captured package logger output.
    stdout : str, optional
        Captured standard output.
    stderr : str, optional
        Captured standard error.
    traceback_text : str, optional
        Traceback text to append when command execution fails.

    Returns
    -------
    str
        Terminal-style block ready to render in the form page.
    """
    header = [f"$ {_quote_argv(argv)}", f"{status.upper()}: {message}".strip()]

    sections: list[str] = []
    if logs.strip():
        sections.append(logs.strip())
    if stdout.strip():
        sections.append(stdout.strip())
    if stderr.strip():
        sections.append("[stderr]\n" + stderr.strip())
    if traceback_text.strip():
        sections.append("[traceback]\n" + traceback_text.strip())

    if not sections:
        sections.append("Command completed without additional terminal output.")

    return "\n".join(header) + "\n\n" + "\n\n".join(sections)



def _sse_event(event: str, data: dict[str, Any]) -> str:
    """
    Serialize one server-sent event block.

    Parameters
    ----------
    event : str
        Event name sent to the browser, such as ``"terminal"`` or ``"done"``.
    data : dict
        JSON-serializable event payload.

    Returns
    -------
    str
        Complete SSE block ending with a blank line.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class _QueueTextWriter:
    """
    File-like object that forwards writes to a streaming event queue.

    The object implements the minimal ``write``/``flush`` interface expected by
    ``redirect_stdout``, ``redirect_stderr``, and :class:`logging.StreamHandler`.

    Parameters
    ----------
    event_queue : queue.Queue
        Queue receiving ``("terminal", payload)`` tuples for the SSE generator.
    prefix : str, optional
        Prefix added to non-empty chunks, used to distinguish stderr output.
    """

    def __init__(self, event_queue: "queue.Queue[tuple[str, dict[str, Any]]]", *, prefix: str = ""):
        """
        Initialize the queue-backed text writer.

        Parameters
        ----------
        event_queue : queue.Queue
            Queue receiving terminal event payloads.
        prefix : str, optional
            Prefix added to non-empty chunks before they are queued.
        """
        self._event_queue = event_queue
        self._prefix = prefix

    def write(self, text: str) -> int:
        """Forward non-empty text to the terminal stream."""
        if not text:
            return 0
        chunk = str(text)
        if self._prefix and chunk.strip():
            chunk = self._prefix + chunk
        self._event_queue.put(
            ("terminal", {"mode": "append", "status": "running", "text": chunk})
        )
        return len(text)

    def flush(self) -> None:
        """Provide the file-like ``flush`` method expected by stream handlers."""
        return None


class _TerminalStreamBridge:
    """
    Bridge delayed interactive GUI callbacks into the original terminal stream.

    Interactive extraction launches a secondary Dash window.  The initial
    ``/run/stream`` request therefore cannot finish when the window opens; it
    must stay alive until the user clicks Extract or exits the interactive
    window.  This bridge is stored in the Dash server config so callbacks in the
    extraction app can append text and emit the final ``done`` event through the
    original form-page terminal.

    Parameters
    ----------
    event_queue : queue.Queue
        Queue drained by the original ``/run/stream`` response generator.
    argv : list of str
        Command tokens shown in the final event payload.
    """

    def __init__(self, event_queue: "queue.Queue[tuple[str, dict[str, Any]]]", argv: list[str]):
        """
        Initialize a terminal stream bridge.

        Parameters
        ----------
        event_queue : queue.Queue
            Queue receiving terminal and completion events.
        argv : list of str
            Parsed command tokens associated with the running command.
        """
        self._event_queue = event_queue
        self._argv = list(argv)
        self._done = False
        self._lock = threading.Lock()

    @property
    def is_done(self) -> bool:
        """
        Return whether the stream has already emitted its final event.

        Returns
        -------
        bool
            ``True`` after :meth:`finish` has queued the final ``done`` event.
        """
        with self._lock:
            return self._done

    def stdout_writer(self) -> _QueueTextWriter:
        """
        Return a writer that appends stdout-like text to the stream.

        Returns
        -------
        _QueueTextWriter
            Writer suitable for ``redirect_stdout``.
        """
        return _QueueTextWriter(self._event_queue)

    def stderr_writer(self) -> _QueueTextWriter:
        """
        Return a writer that appends stderr-like text to the stream.

        Returns
        -------
        _QueueTextWriter
            Writer suitable for ``redirect_stderr``.
        """
        return _QueueTextWriter(self._event_queue, prefix="[stderr] ")

    def logging_handler(self) -> logging.Handler:
        """
        Return a logging handler that writes package logs to the stream.

        Returns
        -------
        logging.Handler
            Handler configured with the package log formatter.
        """
        handler = logging.StreamHandler(self.stdout_writer())
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        handler.setLevel(logging.INFO)
        return handler

    def append(self, text: str, *, status: str = "running") -> None:
        """
        Append terminal text if the stream is still open.

        Parameters
        ----------
        text : str
            Text chunk to append to the terminal panel.
        status : str, optional
            Terminal status associated with the chunk.
        """
        with self._lock:
            if self._done:
                return
        if text:
            self._event_queue.put(
                ("terminal", {"mode": "append", "status": status, "text": text})
            )

    def finish(
        self,
        *,
        status: str,
        message: str,
        output: str | None = None,
        traceback_text: str = "",
    ) -> None:
        """
        Emit a final terminal message and close the stream.

        Parameters
        ----------
        status : str
            Final command status, usually ``"success"`` or ``"error"``.
        message : str
            Final user-facing status message.
        output : str, optional
            Output product path or command result to include in the final event.
        traceback_text : str, optional
            Traceback text appended when the command fails.
        """
        with self._lock:
            if self._done:
                return
            self._done = True

        terminal_status = "success" if status == "success" else "error"
        label = "SUCCESS" if status == "success" else "ERROR"
        text = f"\n{label}: {message}\n"
        if output:
            text += f"Output: {output}\n"
        if traceback_text.strip():
            text += f"\n[traceback]\n{traceback_text}"

        self._event_queue.put(
            ("terminal", {"mode": "append", "status": terminal_status, "text": text})
        )

        data: dict[str, Any] = {
            "status": status,
            "message": message,
            "argv": self._argv,
        }
        if output:
            data["output"] = output
        self._event_queue.put(("done", data))


def _should_defer_terminal_completion(args: argparse.Namespace) -> bool:
    """
    Return whether a parsed command completes later in a secondary GUI.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments.

    Returns
    -------
    bool
        ``True`` for interactive extraction, whose final result is produced by
        callbacks in the secondary extraction window.
    """
    command = getattr(args, "command", None)
    if command in {"show", "show_meta"}:
        return True
    return (
        command == "extract"
        and getattr(args, "shape", None) in {None, "", "interactive"}
    )


def _error_done_event(argv: list[str], message: str, terminal: str) -> str:
    """
    Return an SSE error sequence for validation or parsing failures.

    Parameters
    ----------
    argv : list of str
        Command tokens parsed before the error occurred.
    message : str
        User-facing error message.
    terminal : str
        Terminal panel text to send with the error.

    Returns
    -------
    str
        Concatenated ``terminal`` and ``done`` SSE blocks.
    """
    return _sse_event(
        "terminal",
        {"mode": "replace", "status": "error", "text": terminal},
    ) + _sse_event(
        "done",
        {"status": "error", "message": message, "argv": argv},
    )


def _stream_command_events(payload: dict[str, Any]):
    """
    Yield live command feedback events for a GUI payload.

    The command itself runs in a worker thread while this generator drains a
    queue populated by stdout, stderr, and logging adapters. This lets the web
    page append feedback while the extraction is still running instead of
    waiting for the command to finish.  Interactive extraction receives a
    :class:`_TerminalStreamBridge` so the secondary extraction window can finish
    the same stream after the user selects parameters.

    Parameters
    ----------
    payload : dict
        JSON payload submitted by a command form.

    Yields
    ------
    str
        Serialized server-sent event blocks.
    """
    argv: list[str] = []

    try:
        parser = get_cli_parser()
        argv = payload_to_argv_with_parser(parser, dict(payload))
        if not argv:
            message = "No command provided."
            terminal = _format_terminal_output(argv, status="error", message=message)
            yield _error_done_event(argv, message, terminal)
            return

        set_current_argv(argv)
        args = parser.parse_args(argv)

        if not hasattr(args, "handler"):
            message = "No handler found for command."
            terminal = _format_terminal_output(argv, status="error", message=message)
            yield _error_done_event(argv, message, terminal)
            return

    except CliParseError as exc:
        detail = (exc.message or "").strip()
        message = (
            f"Invalid arguments: {detail}"
            if detail
            else "Invalid arguments. Please check your inputs."
        )
        terminal = _format_terminal_output(argv, status="error", message=message)
        yield _error_done_event(argv, message, terminal)
        return
    except SystemExit:
        message = "Invalid arguments. Please check your inputs."
        terminal = _format_terminal_output(argv, status="error", message=message)
        yield _error_done_event(argv, message, terminal)
        return
    except Exception as exc:
        message = str(exc)
        terminal = _format_terminal_output(
            argv,
            status="error",
            message=message,
            traceback_text="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )
        yield _error_done_event(argv, message, terminal)
        return

    yield _sse_event(
        "terminal",
        {
            "mode": "replace",
            "status": "running",
            "text": f"$ {_quote_argv(argv)}\nRUNNING: Command started. Streaming feedback...\n\n",
        },
    )

    event_queue: "queue.Queue[tuple[str, dict[str, Any]]]" = queue.Queue()
    defer_done = _should_defer_terminal_completion(args)
    if defer_done:
        setattr(args, "_gonet_terminal_stream", _TerminalStreamBridge(event_queue, argv))

    def worker() -> None:
        """Run the parsed command and enqueue its final completion event."""
        final_data = _run_handler_with_terminal_stream(
            args,
            argv,
            event_queue,
            defer_done=defer_done,
        )
        if final_data is not None:
            event_queue.put(("done", final_data))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while True:
        event, data = event_queue.get()
        yield _sse_event(event, data)
        if event == "done":
            break


def _run_handler_with_terminal_stream(
    args: argparse.Namespace,
    argv: list[str],
    event_queue: "queue.Queue[tuple[str, dict[str, Any]]]",
    *,
    defer_done: bool = False,
) -> dict[str, Any] | None:
    """
    Run a command handler while pushing live feedback into an event queue.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command arguments with an attached ``handler`` attribute.
    argv : list of str
        Original command tokens, included in the final event payload.
    event_queue : queue.Queue
        Queue receiving terminal and completion events.
    defer_done : bool, optional
        When ``True``, command completion is delegated to a secondary GUI
        callback, as in interactive extraction.

    Returns
    -------
    dict or None
        Final ``done`` payload for ordinary commands.  Returns ``None`` when a
        secondary GUI callback will finish the stream later.
    """
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    capture_handler = logging.StreamHandler(_QueueTextWriter(event_queue))
    capture_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    capture_handler.setLevel(logging.INFO)

    result: Any = None
    error: Exception | None = None
    traceback_text = ""

    with _COMMAND_RUN_LOCK:
        previous_level = logger.level
        previous_handlers = list(logger.handlers)
        previous_propagate = logger.propagate
        effective_level = logger.getEffectiveLevel()
        if effective_level > logging.INFO:
            logger.setLevel(logging.INFO)

        logger.handlers = [capture_handler]
        logger.propagate = False
        try:
            stdout_writer = _QueueTextWriter(event_queue)
            stderr_writer = _QueueTextWriter(event_queue, prefix="[stderr] ")
            with redirect_stdout(stdout_writer), redirect_stderr(stderr_writer):
                try:
                    result = args.handler(args)
                except Exception as exc:  # stream traceback before returning final error state
                    error = exc
                    traceback_text = "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    event_queue.put(
                        (
                            "terminal",
                            {
                                "mode": "append",
                                "status": "error",
                                "text": f"\nERROR: {exc}\n\n[traceback]\n{traceback_text}",
                            },
                        )
                    )
        finally:
            logger.handlers = previous_handlers
            logger.propagate = previous_propagate
            logger.setLevel(previous_level)

    if error is not None:
        return {"status": "error", "message": str(error), "argv": argv}

    if defer_done:
        command = getattr(args, "command", None)
        if command == "show":
            text = (
                "Show window opened. Interact with the figure, then click Save figure or Exit "
                "in the interactive window to continue.\n"
            )
        elif command == "show_meta":
            text = (
                "Show metadata window opened. Click Save PDF or Exit in the interactive "
                "window to continue.\n"
            )
        else:
            text = (
                "Interactive extraction window opened. "
                "Select the region and click Extract to continue.\n"
            )

        event_queue.put(
            (
                "terminal",
                {
                    "mode": "append",
                    "status": "running",
                    "text": text,
                },
            )
        )
        return None

    message = "Command finished."
    success_text = f"\nSUCCESS: {message}\n"
    if isinstance(result, str) and result.strip():
        success_text += f"Output: {result}\n"
    event_queue.put(
        (
            "terminal",
            {
                "mode": "append",
                "status": "success",
                "text": success_text,
            },
        )
    )
    final_data: dict[str, Any] = {"status": "success", "message": message, "argv": argv}
    if isinstance(result, str) and result.strip():
        final_data["output"] = result
    return final_data


def _run_handler_with_terminal_capture(
    args: argparse.Namespace, argv: list[str]
) -> tuple[Any, str, Exception | None]:
    """Run ``args.handler`` while capturing stdout, stderr, and package logs.

    The GUI is often launched from a frozen desktop app with no visible terminal.
    Capturing command feedback here gives users a single place in the form page
    to inspect progress messages, warnings, and tracebacks. ``stdout`` and
    ``stderr`` redirection is process-global, so command execution is serialized
    with ``_COMMAND_RUN_LOCK`` to avoid mixing output from concurrent form runs.
    """
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    log_buffer = StringIO()

    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    capture_handler = logging.StreamHandler(log_buffer)
    capture_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    capture_handler.setLevel(logging.INFO)

    result: Any = None
    error: Exception | None = None
    traceback_text = ""

    with _COMMAND_RUN_LOCK:
        previous_level = logger.level
        previous_handlers = list(logger.handlers)
        previous_propagate = logger.propagate
        effective_level = logger.getEffectiveLevel()
        if effective_level > logging.INFO:
            logger.setLevel(logging.INFO)

        logger.handlers = [capture_handler]
        logger.propagate = False
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                try:
                    result = args.handler(args)
                except Exception as exc:  # return captured output alongside the error
                    error = exc
                    traceback_text = "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )
        finally:
            logger.handlers = previous_handlers
            logger.propagate = previous_propagate
            logger.setLevel(previous_level)

    status = "error" if error is not None else "success"
    message = str(error) if error is not None else f"Executed: {' '.join(argv)}"
    terminal_output = _format_terminal_output(
        argv,
        status=status,
        message=message,
        logs=log_buffer.getvalue(),
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
        traceback_text=traceback_text,
    )

    return result, terminal_output, error


# ----------------------------
# Payload -> argv conversion
# ----------------------------

def _truthy(v: Any) -> bool:
    """
    Interpret common GUI boolean representations.

    Parameters
    ----------
    v : :class:`object`
        Value from a GUI payload.

    Returns
    -------
    :class:`bool`
        ``True`` if the value resembles a truthy checkbox-like value.
    """
    if v is True:
        return True
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "on", "yes", "y"}
    return False


def _split_csv_tokens(s: str) -> list[str]:
    """
    Split a comma-separated string into CLI tokens.

    Parameters
    ----------
    s : :class:`str`
        Comma-separated token string.

    Returns
    -------
    :class:`list` of :class:`str`
        Non-empty, stripped tokens.
    """
    return [p.strip() for p in s.split(",") if p.strip()]


def _get_final_subparser(root: argparse.ArgumentParser, cmd_tokens: list[str]) -> argparse.ArgumentParser:
    """
    Resolve the final argparse subparser for a command token sequence.

    Parameters
    ----------
    root : :class:`argparse.ArgumentParser`
        Root parser containing the command tree.
    cmd_tokens : :class:`list` of :class:`str`
        Command token sequence (e.g. ``["connect", "snap"]``).

    Returns
    -------
    :class:`argparse.ArgumentParser`
        The most specific subparser that can be reached by walking ``cmd_tokens``.

    Notes
    -----
    If a token does not correspond to a known subparser choice, traversal stops
    and the current parser is returned.
    """
    parser = root
    for tok in cmd_tokens:
        sp_action = next(
            (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)),
            None,
        )
        if sp_action is None:
            break
        if tok not in sp_action.choices:
            break
        parser = sp_action.choices[tok]
    return parser


def _option_string_for_dest(parser: argparse.ArgumentParser, dest: str) -> str:
    """Return the argparse option string registered for ``dest``.

    GUI form field names are keyed by argparse destinations (for example
    ``inner_radius``). The actual CLI option may contain underscores or hyphens,
    so this helper asks the parser instead of guessing.
    """
    for action in parser._actions:
        if action.dest != dest:
            continue

        long_options = [opt for opt in action.option_strings if opt.startswith("--")]
        if long_options:
            return long_options[0]
        if action.option_strings:
            return action.option_strings[0]

    return f"--{dest}"


def payload_to_argv_with_parser(root: argparse.ArgumentParser, payload: dict) -> list[str]:
    """
    Convert a GUI payload into an ``argv`` list using argparse metadata.

    The conversion uses the destination names and action ordering from the final
    command parser to place positional arguments first and options afterward.

    Parameters
    ----------
    root : :class:`argparse.ArgumentParser`
        Root parser containing the full command tree.
    payload : :class:`dict`
        GUI payload containing:

        - ``command``: command token string (e.g. ``"show"`` or ``"extract"``)
        - additional form fields keyed by argparse dest name

    Returns
    -------
    :class:`list` of :class:`str`
        Token list suitable for :meth:`argparse.ArgumentParser.parse_args`.

    Notes
    -----
    - Positionals with multi-value ``nargs`` are commonly provided as a single
      comma-separated string by the GUI; these values are split into tokens.
    - Boolean checkbox fields are treated as ``store_true`` flags and only emit
      the option flag when truthy.
    """
    cmd = payload.pop("command", None)
    if not cmd:
        return []

    cmd_tokens = str(cmd).split()
    cmd_parser = _get_final_subparser(root, cmd_tokens)

    positional_actions = [
        a
        for a in cmd_parser._actions
        if getattr(a, "option_strings", None) == [] and a.dest != "help"
    ]
    positional_dests = [a.dest for a in positional_actions]

    argv: list[str] = []
    argv += cmd_tokens

    # 1) add positionals in order
    for dest in positional_dests:
        if dest not in payload:
            continue
        val = payload.pop(dest)

        if isinstance(val, str):
            argv += _split_csv_tokens(val)
        elif isinstance(val, list):
            for item in val:
                argv += _split_csv_tokens(str(item))
        else:
            argv.append(str(val))

    # 2) add options (everything remaining in payload)
    for key, val in payload.items():
        if val is None or val == "":
            continue

        flag = _option_string_for_dest(cmd_parser, key)

        # Boolean flags
        if isinstance(val, bool) or (
            isinstance(val, str)
            and val.strip().lower()
            in {"on", "true", "false", "1", "0", "yes", "no", "y", "n"}
        ):
            if _truthy(val):
                argv.append(flag)
            continue

        # Lists become repeated positional tokens
        if isinstance(val, list):
            argv.append(flag)
            argv.extend(str(v) for v in val)
            continue

        # Everything else is passed as an explicit option assignment. This
        # avoids argparse mistaking negative values such as ``-90,180`` for
        # option-like tokens.
        argv.append(f"{flag}={val}")

    return argv
