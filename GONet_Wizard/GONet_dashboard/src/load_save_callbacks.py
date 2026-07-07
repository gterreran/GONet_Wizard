"""
Reusable JSON save and load helpers for Dash applications.

The save helper uses the native pywebview save dialog in the desktop app and a
browser save picker, when available, in a regular browser. In every code path,
the selected filename is restricted or normalized to the ``.json`` extension.

Functions
---------
:func:`register_json_download`
    Register a clientside callback that saves JSON data through a user-visible
    save dialog.
:func:`stage_json_download`
    Serialize a large JSON payload once and expose a short-lived descriptor.
:func:`register_staged_json_download`
    Register the optimized save flow for staged JSON payloads.
:func:`load_json`
    Decode a base64-encoded JSON data URL.
"""

import base64
from collections import OrderedDict
import json
from pathlib import Path
import threading
import time
from typing import Any
import uuid

from flask import Response, abort


_STAGED_JSON_LOCK = threading.Lock()
_STAGED_JSON_PAYLOADS = OrderedDict()
_STAGED_JSON_TTL_SECONDS = 15 * 60
_STAGED_JSON_MAX_ITEMS = 8


def _normalize_json_filename(filename: Any, default: str = "data.json") -> str:
    """Return a non-empty filename whose final suffix is ``.json``."""
    clean_name = str(filename or "").strip() or default
    output_path = Path(clean_name)
    name = output_path.name.rstrip(".")
    suffix = Path(name).suffix
    stem = name[: -len(suffix)] if suffix else name
    return str(output_path.with_name(f"{stem}.json"))


def _prune_staged_json(now: float | None = None) -> None:
    """Discard expired or surplus staged JSON payloads.

    The cache is intentionally small because staged exports are only a bridge
    between a Dash callback and the immediately following save operation.
    """
    current_time = time.monotonic() if now is None else now

    expired = [
        token
        for token, (created_at, _, _) in _STAGED_JSON_PAYLOADS.items()
        if current_time - created_at > _STAGED_JSON_TTL_SECONDS
    ]
    for token in expired:
        _STAGED_JSON_PAYLOADS.pop(token, None)

    while len(_STAGED_JSON_PAYLOADS) > _STAGED_JSON_MAX_ITEMS:
        _STAGED_JSON_PAYLOADS.popitem(last=False)


def stage_json_download(
    data: Any,
    default_filename: str = "data.json",
) -> dict[str, str]:
    """Serialize JSON once and stage it behind a short-lived local URL.

    Returning a tiny descriptor instead of the full export prevents Dash from
    serializing a large payload into a browser ``dcc.Store`` and, in the
    desktop application, prevents pywebview from marshaling that payload back
    into Python a second time.
    """
    filename = _normalize_json_filename(default_filename)
    payload = json.dumps(
        data,
        indent=2,
        default=str,
        allow_nan=False,
    ).encode("utf-8")
    token = uuid.uuid4().hex

    with _STAGED_JSON_LOCK:
        _prune_staged_json()
        _STAGED_JSON_PAYLOADS[token] = (time.monotonic(), payload, filename)
        while len(_STAGED_JSON_PAYLOADS) > _STAGED_JSON_MAX_ITEMS:
            _STAGED_JSON_PAYLOADS.popitem(last=False)

    return {
        "token": token,
        "url": f"/_gonet_json_download/{token}",
        "filename": filename,
    }


def _consume_staged_json(token: str) -> tuple[bytes, str] | None:
    """Remove and return a staged JSON payload by token."""
    with _STAGED_JSON_LOCK:
        _prune_staged_json()
        staged = _STAGED_JSON_PAYLOADS.pop(str(token), None)

    if staged is None:
        return None

    _, payload, filename = staged
    return payload, filename


def register_staged_json_route(server) -> None:
    """Register the one-time local endpoint serving staged JSON exports."""
    endpoint = "gonet_staged_json_download"
    if endpoint in server.view_functions:
        return

    @server.get("/_gonet_json_download/<token>", endpoint=endpoint)
    def staged_json_download(token):
        staged = _consume_staged_json(token)
        if staged is None:
            abort(404)

        payload, filename = staged
        response = Response(payload, mimetype="application/json")
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )
        response.headers["Content-Length"] = str(len(payload))
        response.headers["Cache-Control"] = "no-store"
        return response


def register_json_download(
    app,
    output_component,
    input_component,
    default_filename: str = "data.json",
):
    """Register a reusable clientside callback for saving JSON data.

    In the desktop application, the callback delegates to the exposed
    ``window.pywebview.api.download_json`` method, which opens the operating
    system's native save dialog. In a regular browser it uses the File System
    Access API when available, falling back to a filename prompt and standard
    browser download.

    Parameters
    ----------
    app : dash.Dash
        Dash application on which to register the callback.
    output_component : dash.Output
        Dummy output used to satisfy Dash's callback contract.
    input_component : dash.Input
        Component property containing the JSON-serializable data to save.
    default_filename : str, optional
        Suggested output filename. Any supplied suffix is replaced by
        ``.json`` before the callback is registered.
    """
    normalized_default = _normalize_json_filename(default_filename)
    clientside_function = r"""
        async function(data) {
            if (data === null || data === undefined) {
                return window.dash_clientside.no_update;
            }

            const defaultFilename = __DEFAULT_FILENAME__;

            function ensureJsonExtension(filename) {
                const cleanName = String(filename || "").trim();
                if (!cleanName) {
                    return defaultFilename;
                }

                const slashIndex = Math.max(
                    cleanName.lastIndexOf("/"),
                    cleanName.lastIndexOf("\\")
                );
                const dotIndex = cleanName.lastIndexOf(".");
                const hasExtension = dotIndex > slashIndex + 1;
                const stem = hasExtension ? cleanName.slice(0, dotIndex) : cleanName;
                return stem + ".json";
            }

            try {
                if (
                    window.pywebview &&
                    window.pywebview.api &&
                    typeof window.pywebview.api.download_json === "function"
                ) {
                    await window.pywebview.api.download_json(data, defaultFilename);
                    return "";
                }

                const jsonString = JSON.stringify(data, null, 2);
                const blob = new Blob([jsonString], {type: "application/json"});

                if (typeof window.showSaveFilePicker === "function") {
                    let suggestedName = defaultFilename;
                    let handle = null;

                    while (!handle) {
                        const candidate = await window.showSaveFilePicker({
                            suggestedName: suggestedName,
                            types: [{
                                description: "JSON files",
                                accept: {"application/json": [".json"]}
                            }],
                            excludeAcceptAllOption: true
                        });

                        if (candidate.name.toLowerCase().endsWith(".json")) {
                            handle = candidate;
                        } else {
                            suggestedName = ensureJsonExtension(candidate.name);
                            alert("JSON files must use the .json extension.");
                        }
                    }

                    const writable = await handle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    return "";
                }

                const requestedName = prompt(
                    "Please enter the filename:",
                    defaultFilename
                );
                if (!requestedName || requestedName.trim() === "") {
                    return window.dash_clientside.no_update;
                }

                const url = URL.createObjectURL(blob);
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = ensureJsonExtension(requestedName);
                document.body.appendChild(anchor);
                anchor.click();
                document.body.removeChild(anchor);
                URL.revokeObjectURL(url);
                return "";
            } catch (error) {
                if (error && error.name === "AbortError") {
                    return window.dash_clientside.no_update;
                }

                console.error("JSON save error:", error);
                alert("Save failed.");
                return window.dash_clientside.no_update;
            }
        }
    """.replace("__DEFAULT_FILENAME__", json.dumps(normalized_default))

    app.clientside_callback(
        clientside_function,
        output_component,
        input_component,
        prevent_initial_call=True,
    )


def register_staged_json_download(
    app,
    output_component,
    input_component,
    default_filename: str = "data.json",
):
    """Register a save callback for server-staged JSON payloads.

    The input component must contain the descriptor returned by
    :func:`stage_json_download`. The browser receives only that small
    descriptor. In pywebview, Python downloads the staged bytes directly from
    the local Dash server after the user selects a destination. In a regular
    browser, JavaScript fetches the same one-time URL after the save picker is
    confirmed.
    """
    normalized_default = _normalize_json_filename(default_filename)
    register_staged_json_route(app.server)

    clientside_function = r"""
        async function(descriptor) {
            if (
                descriptor === null ||
                descriptor === undefined ||
                !descriptor.url
            ) {
                return window.dash_clientside.no_update;
            }

            const fallbackFilename = __DEFAULT_FILENAME__;

            function ensureJsonExtension(filename) {
                const cleanName = String(filename || "").trim();
                if (!cleanName) {
                    return fallbackFilename;
                }

                const slashIndex = Math.max(
                    cleanName.lastIndexOf("/"),
                    cleanName.lastIndexOf("\\")
                );
                const dotIndex = cleanName.lastIndexOf(".");
                const hasExtension = dotIndex > slashIndex + 1;
                const stem = hasExtension ? cleanName.slice(0, dotIndex) : cleanName;
                return stem + ".json";
            }

            const defaultFilename = ensureJsonExtension(
                descriptor.filename || fallbackFilename
            );
            const downloadUrl = new URL(
                descriptor.url,
                window.location.href
            ).href;

            async function fetchBlob() {
                const response = await fetch(downloadUrl, {cache: "no-store"});
                if (!response.ok) {
                    throw new Error(
                        "Export download failed with status " + response.status
                    );
                }
                return await response.blob();
            }

            try {
                if (
                    window.pywebview &&
                    window.pywebview.api &&
                    typeof window.pywebview.api.download_json_url === "function"
                ) {
                    await window.pywebview.api.download_json_url(
                        downloadUrl,
                        defaultFilename
                    );
                    return "";
                }

                if (typeof window.showSaveFilePicker === "function") {
                    let suggestedName = defaultFilename;
                    let handle = null;

                    while (!handle) {
                        const candidate = await window.showSaveFilePicker({
                            suggestedName: suggestedName,
                            types: [{
                                description: "JSON files",
                                accept: {"application/json": [".json"]}
                            }],
                            excludeAcceptAllOption: true
                        });

                        if (candidate.name.toLowerCase().endsWith(".json")) {
                            handle = candidate;
                        } else {
                            suggestedName = ensureJsonExtension(candidate.name);
                            alert("JSON files must use the .json extension.");
                        }
                    }

                    const blob = await fetchBlob();
                    const writable = await handle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    return "";
                }

                const requestedName = prompt(
                    "Please enter the filename:",
                    defaultFilename
                );
                if (!requestedName || requestedName.trim() === "") {
                    return window.dash_clientside.no_update;
                }

                const blob = await fetchBlob();
                const url = URL.createObjectURL(blob);
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = ensureJsonExtension(requestedName);
                document.body.appendChild(anchor);
                anchor.click();
                document.body.removeChild(anchor);
                URL.revokeObjectURL(url);
                return "";
            } catch (error) {
                if (error && error.name === "AbortError") {
                    return window.dash_clientside.no_update;
                }

                console.error("JSON save error:", error);
                alert("Save failed.");
                return window.dash_clientside.no_update;
            }
        }
    """.replace("__DEFAULT_FILENAME__", json.dumps(normalized_default))

    app.clientside_callback(
        clientside_function,
        output_component,
        input_component,
        prevent_initial_call=True,
    )


def load_json(contents: str) -> dict:
    """Decode a base64-encoded JSON data URL into a Python dictionary.

    Parameters
    ----------
    contents : str
        Data URL containing base64-encoded JSON content.

    Returns
    -------
    dict
        Parsed JSON content.

    Raises
    ------
    ValueError
        If the data URL cannot be decoded or parsed as JSON.
    """
    try:
        encoded = contents.split(",")[1]
        padding_needed = (4 - len(encoded) % 4) % 4
        encoded += "=" * padding_needed
        decoded = base64.b64decode(encoded).decode("utf-8")
        return json.loads(decoded)
    except (
        IndexError,
        base64.binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ValueError(f"Invalid JSON base64 data: {error}") from error
