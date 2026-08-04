from __future__ import annotations

from queue import Queue

from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app as extract_app
from GONet_Wizard.GONet_utils.src.extract_app.extract_layout import create_layout
from GONet_Wizard.ui import dash_runner
from GONet_Wizard.ui.dash_runner import DashLaunchSpec


class DummyThread:
    def is_alive(self) -> bool:
        return True


class DummyApp:
    layout = None
    index_string = None


def _find_component(component, component_id):
    if getattr(component, "id", None) == component_id:
        return component

    children = getattr(component, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]

    for child in children:
        found = _find_component(child, component_id)
        if found is not None:
            return found
    return None


def test_extract_layout_rebuilds_file_dropdown_from_current_config(tmp_path):
    first_file = tmp_path / "1.jpg"
    second_file = tmp_path / "2.jpg"

    extract_app.server.config["data_files"] = [str(first_file)]
    first_layout = create_layout()
    first_dropdown = _find_component(first_layout, "file-selector")

    extract_app.server.config["data_files"] = [str(second_file)]
    second_layout = create_layout()
    second_dropdown = _find_component(second_layout, "file-selector")

    assert first_dropdown.options == [{"label": "1.jpg", "value": str(first_file)}]
    assert first_dropdown.value == str(first_file)
    assert second_dropdown.options == [{"label": "2.jpg", "value": str(second_file)}]
    assert second_dropdown.value == str(second_file)


def test_ensure_dash_running_reconfigures_reused_server(monkeypatch):
    app = DummyApp()
    calls = []

    def configure(target_app):
        calls.append("configure")
        target_app.configured = len(calls)

    def layout(target_app):
        return f"layout-{target_app.configured}"

    spec = DashLaunchSpec(
        app=app,
        app_key="test-reuse",
        configure=configure,
        layout=layout,
        register_callbacks=lambda: calls.append("callbacks"),
    )
    key = (spec.app_key, 9999)
    monkeypatch.setitem(
        dash_runner._RUNNERS,
        key,
        dash_runner._RunnerState(
            thread=DummyThread(),
            port=9999,
            startup_errors=Queue(),
        ),
    )

    url = dash_runner.ensure_dash_running(spec, debug=False, port=9999)

    assert url == "http://127.0.0.1:9999"
    assert calls == ["configure"]
    assert app.layout == "layout-1"
