"""Tests for JSON filename normalization and save-dialog integration."""

import io
import json

import pytest
from flask import Flask

from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import (
    _normalize_json_filename,
    register_json_download,
    register_staged_json_download,
    stage_json_download,
)
from GONet_Wizard.ui.api import WebviewAPI, _ensure_json_extension


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("status", "status.json"),
        ("status.txt", "status.json"),
        ("status.JSON", "status.json"),
        ("archive.status.txt", "archive.status.json"),
        (".status", ".status.json"),
        ("status.", "status.json"),
    ],
)
def test_json_filename_normalizers_force_json_extension(filename, expected):
    """Both browser and native helpers should apply identical suffix rules."""
    assert _normalize_json_filename(filename) == expected
    assert _ensure_json_extension(filename) == expected


def test_normalize_json_filename_uses_default_for_empty_name():
    """An empty suggested name should still produce a useful JSON filename."""
    assert _normalize_json_filename("", default="dashboard_status.csv") == (
        "dashboard_status.json"
    )


class _CallbackSpyApp:
    def __init__(self):
        self.calls = []
        self.server = Flask(f"callback-spy-{id(self)}")

    def clientside_callback(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_register_json_download_embeds_normalized_default_and_save_picker():
    """The shared client callback should expose a Save As flow for JSON only."""
    app = _CallbackSpyApp()
    output = object()
    input_ = object()

    register_json_download(
        app,
        output,
        input_,
        default_filename="filtered_data.csv",
    )

    assert len(app.calls) == 1
    args, kwargs = app.calls[0]
    script, registered_output, registered_input = args

    assert registered_output is output
    assert registered_input is input_
    assert kwargs == {"prevent_initial_call": True}
    assert 'const defaultFilename = "filtered_data.json";' in script
    assert "window.showSaveFilePicker" in script
    assert "await window.pywebview.api.download_json(data, defaultFilename)" in script
    assert 'accept: {"application/json": [".json"]}' in script
    assert "anchor.download = ensureJsonExtension(requestedName)" in script


def test_register_staged_json_download_uses_url_instead_of_payload_bridge():
    """Large exports should be fetched from a one-time local URL."""
    app = _CallbackSpyApp()
    output = object()
    input_ = object()

    register_staged_json_download(
        app,
        output,
        input_,
        default_filename="filtered_data.csv",
    )

    args, kwargs = app.calls[0]
    script, registered_output, registered_input = args

    assert registered_output is output
    assert registered_input is input_
    assert kwargs == {"prevent_initial_call": True}
    assert 'const fallbackFilename = "filtered_data.json";' in script
    assert "download_json_url" in script
    assert "await fetch(downloadUrl" in script
    assert "download_json(data" not in script
    assert "gonet_staged_json_download" in app.server.view_functions


def test_staged_json_route_serves_payload_once():
    """Staged payloads should be serialized once and released after reading."""
    app = _CallbackSpyApp()
    register_staged_json_download(app, object(), object())
    descriptor = stage_json_download({"value": 3}, "result.txt")

    response = app.server.test_client().get(descriptor["url"])

    assert response.status_code == 200
    assert response.get_json() == {"value": 3}
    assert response.headers["Cache-Control"] == "no-store"
    assert "result.json" in response.headers["Content-Disposition"]
    assert app.server.test_client().get(descriptor["url"]).status_code == 404


def test_download_json_normalizes_suggested_and_selected_paths(tmp_path, monkeypatch):
    """Native saves should replace a user-entered non-JSON extension."""
    api = WebviewAPI()
    selected_path = tmp_path / "my_saved_status.csv"
    calls = []

    def fake_pick_save_path(default_name, file_types):
        calls.append((default_name, file_types))
        return str(selected_path)

    monkeypatch.setattr(api, "pick_save_path", fake_pick_save_path)

    written_path = api.download_json(
        {"channels": ["red", "green"]},
        default_name="dashboard_status.txt",
    )

    expected_path = tmp_path / "my_saved_status.json"
    assert calls == [("dashboard_status.json", ("JSON files (*.json)",))]
    assert written_path == str(expected_path)
    assert not selected_path.exists()
    assert json.loads(expected_path.read_text(encoding="utf-8")) == {
        "channels": ["red", "green"]
    }


def test_download_json_returns_empty_string_when_save_is_canceled(monkeypatch):
    """Canceling the native dialog should not attempt to write a file."""
    api = WebviewAPI()
    monkeypatch.setattr(api, "pick_save_path", lambda **_: "")

    assert api.download_json({"value": 1}, "status.json") == ""


def test_download_json_url_streams_local_payload_to_selected_path(
    tmp_path,
    monkeypatch,
):
    """The desktop bridge should transfer bytes without marshaling JSON data."""
    from GONet_Wizard.ui import api as api_module

    api = WebviewAPI()
    selected_path = tmp_path / "filtered_data.csv"
    payload = b'{"value": 7}'

    monkeypatch.setattr(
        api,
        "pick_save_path",
        lambda **_: str(selected_path),
    )
    monkeypatch.setattr(
        api_module,
        "urlopen",
        lambda *_args, **_kwargs: io.BytesIO(payload),
    )

    written_path = api.download_json_url(
        "http://127.0.0.1:8050/_gonet_json_download/token",
        "filtered_data.txt",
    )

    expected_path = tmp_path / "filtered_data.json"
    assert written_path == str(expected_path)
    assert expected_path.read_bytes() == payload


def test_download_json_url_rejects_non_local_urls(monkeypatch):
    """The desktop API must not expose a general remote downloader."""
    api = WebviewAPI()
    monkeypatch.setattr(
        api,
        "pick_save_path",
        lambda **_: pytest.fail("dialog should not open"),
    )

    with pytest.raises(ValueError, match="Only local"):
        api.download_json_url("https://example.com/data.json")


def _component_ids(component):
    """Yield IDs from a Dash component tree."""
    component_id = getattr(component, "id", None)
    if component_id is not None:
        yield component_id

    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]

    for child in children:
        if hasattr(child, "children") or hasattr(child, "id"):
            yield from _component_ids(child)


def test_dashboard_layout_uses_stores_for_both_json_save_flows():
    """Export and status saves should both feed the shared Save As callback."""
    from GONet_Wizard.GONet_dashboard.src.layout import layout

    component_ids = set(_component_ids(layout([])))

    assert {
        "export-epoch-indices",
        "export-data-json",
        "export-save-dummy",
        "status-data",
        "status-save-dummy",
    }.issubset(component_ids)
    assert "download-json" not in component_ids
