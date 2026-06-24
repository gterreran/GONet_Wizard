from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import json

import pandas as pd
import pytest

from GONet_Wizard.commands import extract as extract_command


def test_comma_separated_pair_parses_two_integers():
    assert extract_command.comma_separated_pair("10,20", "center") == (10, 20)


@pytest.mark.parametrize("value", ["10", "10,20,30", "10,bad"])
def test_comma_separated_pair_rejects_invalid_input(value):
    with pytest.raises(ValueError, match="--center"):
        extract_command.comma_separated_pair(value, "center")


def test_validate_output_file_adds_default_json_extension(tmp_path):
    with pytest.warns(RuntimeWarning, match="Defaulting to 'json'"):
        output, output_type = extract_command.validate_output_file(str(tmp_path / "counts"), None)

    assert output == str(tmp_path / "counts.json")
    assert output_type == "json"


def test_validate_output_file_uses_requested_extension_when_missing(tmp_path):
    output, output_type = extract_command.validate_output_file(str(tmp_path / "counts"), "csv")

    assert output == str(tmp_path / "counts.csv")
    assert output_type == "csv"


def test_validate_output_file_rejects_unsupported_extension(tmp_path):
    with pytest.raises(ValueError, match="json or .csv"):
        extract_command.validate_output_file(str(tmp_path / "counts.txt"), None)


def test_validate_output_file_uses_extension_over_conflicting_output_type(tmp_path):
    with pytest.warns(RuntimeWarning, match="does not match"):
        output, output_type = extract_command.validate_output_file(str(tmp_path / "counts.json"), "csv")

    assert output == str(tmp_path / "counts.json")
    assert output_type == "json"


def test_validate_output_file_creates_parent_directory(tmp_path):
    output = tmp_path / "new" / "nested" / "counts.json"

    returned, output_type = extract_command.validate_output_file(str(output), None)

    assert returned == str(output)
    assert output_type == "json"
    assert output.parent.exists()


def test_validate_output_file_avoids_overwriting_existing_file(tmp_path):
    existing = tmp_path / "counts.json"
    existing.write_text("{}")

    returned, output_type = extract_command.validate_output_file(str(existing), None)

    assert returned == str(tmp_path / "counts_1.json")
    assert output_type == "json"


def test_extract_counts_from_gonet_writes_json_and_builds_circle_params(tmp_path, monkeypatch):
    calls = []

    def fake_extract_all(files, channels, extraction_params):
        calls.append((files, channels, extraction_params))
        return [{"filename": "a.jpg", "red": {"total_counts": 10}}]

    monkeypatch.setattr(extract_command, "extract_all", fake_extract_all)
    output = tmp_path / "counts.json"

    extract_command.extract_counts_from_GONet(
        files="a.jpg,b.jpg",
        red=True,
        shape="circle",
        center="10,20",
        radius=5,
        angles="0,90",
        output=str(output),
    )

    assert calls == [(
        ["a.jpg", "b.jpg"],
        ["red"],
        {
            "shape": "circle",
            "x0": 10,
            "y0": 20,
            "param1": 5,
            "param2": None,
            "start_angle": 0,
            "end_angle": 90,
            "path": None,
        },
    )]
    assert json.loads(output.read_text()) == [{"filename": "a.jpg", "red": {"total_counts": 10}}]


def test_extract_counts_from_gonet_defaults_to_all_channels(tmp_path, monkeypatch):
    calls = []

    def fake_extract_all(files, channels, extraction_params):
        calls.append((files, channels, extraction_params))
        return [{"filename": "a.jpg"}]

    monkeypatch.setattr(extract_command, "extract_all", fake_extract_all)

    extract_command.extract_counts_from_GONet(
        files=["a.jpg"],
        shape="rectangle",
        center="10,20",
        sides="4,6",
        output=str(tmp_path / "counts.json"),
    )

    assert calls[0][1] == ["red", "green", "blue"]
    assert calls[0][2]["param1"] == 4
    assert calls[0][2]["param2"] == 6


def test_extract_counts_from_gonet_writes_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(
        extract_command,
        "extract_all",
        lambda files, channels, extraction_params: [{"filename": "a.jpg", "red": {"total_counts": 10}}],
    )
    output = tmp_path / "counts.csv"

    extract_command.extract_counts_from_GONet(
        files=["a.jpg"],
        green=True,
        shape="annulus",
        center="10,20",
        inner_radius=2,
        outer_radius=5,
        output=str(output),
        output_type="csv",
    )

    df = pd.read_csv(output)
    assert list(df.columns) == ["filename", "red_total_counts"]
    assert df.loc[0, "filename"] == "a.jpg"
    assert df.loc[0, "red_total_counts"] == 10


def test_extract_counts_from_gonet_requires_shape_specific_parameters(tmp_path):
    with pytest.raises(ValueError, match="--center"):
        extract_command.extract_counts_from_GONet(
            files=["a.jpg"],
            shape="circle",
            radius=5,
            output=str(tmp_path / "counts.json"),
        )

    with pytest.raises(ValueError, match="--radius"):
        extract_command.extract_counts_from_GONet(
            files=["a.jpg"],
            shape="circle",
            center="1,2",
            output=str(tmp_path / "counts.json"),
        )

    with pytest.raises(ValueError, match="inner_radius"):
        extract_command.extract_counts_from_GONet(
            files=["a.jpg"],
            shape="annulus",
            center="1,2",
            inner_radius=1,
            output=str(tmp_path / "counts.json"),
        )


def test_extract_counts_from_gonet_returns_when_interactive_gui_cancelled(tmp_path, monkeypatch):
    import sys
    import types

    fake_gui = types.ModuleType("GONet_Wizard.GONet_utils.src.extract_app.extract_gui")
    fake_gui.launch_extraction_gui = lambda files: None
    monkeypatch.setitem(sys.modules, fake_gui.__name__, fake_gui)

    extract_command.extract_counts_from_GONet(
        files=["a.jpg"],
        shape=None,
        output=str(tmp_path / "unused.json"),
    )

    assert not (tmp_path / "unused.json").exists()


def test_cli_handler_noninteractive_filters_files_and_delegates(monkeypatch, tmp_path):
    calls = []
    files = [tmp_path / "a.jpg", tmp_path / "b.txt"]

    monkeypatch.setattr(extract_command, "filter_by_ext", lambda values, exts: [values[0]])
    monkeypatch.setattr(
        extract_command,
        "extract_counts_from_GONet",
        lambda **kwargs: calls.append(kwargs),
    )

    args = SimpleNamespace(
        filenames=files,
        red=True,
        green=False,
        blue=False,
        shape="circle",
        center="1,2",
        radius="3",
        sides=None,
        inner_radius=None,
        outer_radius=None,
        angles=None,
        output="out.json",
        output_type="json",
        debug=False,
        port=8051,
    )

    assert extract_command.cli_handler(args) is None
    assert calls[0]["files"] == [files[0]]
    assert calls[0]["radius"] == 3.0
    assert calls[0]["shape"] == "circle"


def test_cli_handler_interactive_returns_window_request(monkeypatch, tmp_path):
    import sys
    import types

    fake_gui = types.ModuleType("GONet_Wizard.GONet_utils.src.extract_app.extract_gui")
    launch_calls = []

    def fake_ensure_extraction_gui_running(
        data_files,
        debug,
        port,
        channels=None,
        output=None,
        output_type=None,
    ):
        launch_calls.append({
            "data_files": data_files,
            "debug": debug,
            "port": port,
            "channels": channels,
            "output": output,
            "output_type": output_type,
        })
        return "http://127.0.0.1:8051"

    fake_gui.ensure_extraction_gui_running = fake_ensure_extraction_gui_running
    monkeypatch.setitem(sys.modules, fake_gui.__name__, fake_gui)
    monkeypatch.setattr(extract_command, "filter_by_ext", lambda values, exts: values)

    args = SimpleNamespace(
        filenames=[tmp_path / "a.jpg"],
        red=False,
        green=False,
        blue=False,
        shape="interactive",
        center=None,
        radius=None,
        sides=None,
        inner_radius=None,
        outer_radius=None,
        angles=None,
        output=None,
        output_type=None,
        debug=True,
        port=8051,
    )

    result = extract_command.cli_handler(args)

    assert result.key == "extract-gui"
    assert result.spec.url == "http://127.0.0.1:8051"
    assert launch_calls == [{
        "data_files": [str(tmp_path / "a.jpg")],
        "debug": True,
        "port": 8051,
        "channels": ["red", "green", "blue"],
        "output": None,
        "output_type": None,
    }]
