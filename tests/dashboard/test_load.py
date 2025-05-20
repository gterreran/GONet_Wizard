import sys, pytest, os, json

from unittest.mock import patch

from GONet_Wizard.commands import run_dashboard
from GONet_Wizard.__main__ import main

@pytest.fixture(autouse=True)
def disable_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("Unexpected call to input()"))

def test_cli_dispatch_fallback(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["GONet_Wizard"])
    with patch("argparse.ArgumentParser.print_help") as mock_help:
        main()
        mock_help.assert_called_once()

def test_cli_dispatch_dashboard(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["GONet_Wizard", "dashboard"])
    with patch("GONet_Wizard.__main__.commands.run") as mock_run:
        main()
        mock_run.assert_called_once()

def test_run_dashboard_success():
    with patch("GONet_Wizard.commands.run_dashboard.app.run_server") as mock_run:
        run_dashboard.run()
        mock_run.assert_called_once_with(debug=True)

#%%%%%%%%%%%%%%%%%%%%%%
from GONet_Wizard.GONet_dashboard.src import env
from GONet_Wizard.GONet_dashboard.src.callbacks import load
from GONet_Wizard.GONet_dashboard.src.hood import load_data

# One-time setup 
os.environ["GONET_ROOT"] = "tests/test_dashboard_data/"
os.environ["ROOT_EXT"] = "fake/path/"
env.ROOT = os.environ["GONET_ROOT"]
env.ROOT_EXT = os.environ["ROOT_EXT"]

def test_load_data_from_json_success():
    # Accounting for the hidden State for `alert-container.className`
    result = load('', None)

    assert isinstance(result, tuple)
    assert len(result) == 3 + 3

    data, opt_x, opt_y, _, _, _ = result

    assert isinstance(data, dict)
    assert "idx" in data
    assert "channel" in data
    assert len(data["idx"]) > 0
    assert opt_x == opt_y
    assert all(isinstance(opt, dict) and "label" in opt and "value" in opt for opt in opt_x)


def test_color_ratios_present():
    data = load_data.load_data_from_json(env)
    for ratio in ["blue-green", "green-red", "blue-red"]:
        assert ratio in data
        assert all(isinstance(v, float) for v in data[ratio] if v is not None)

def test_each_channel_has_fits():
    data = load_data.load_data_from_json(env)
    n_channels = len(env.CHANNELS)
    for label in env.LABELS['fit']:
        assert label in data
        assert len(data[label]) == len(data["idx"])
        assert len(data[label]) % n_channels == 0

def test_load_data_from_json_fails_with_bad_json(tmp_path):
    # Setup: create a bad JSON file
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ not: valid json ")

    # Point env.ROOT to this temp directory
    env.DASHBOARD_DATA_PATH = tmp_path

    with pytest.raises(ValueError, match="Failed to parse JSON file"):
        load_data.load_data_from_json(env)


def test_load_data_from_json_fails_with_missing_directory(tmp_path):
    # Point to non-existent subdir
    missing_dir = tmp_path / "does_not_exist"
    env.DASHBOARD_DATA_PATH = missing_dir

    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_data.load_data_from_json(env)


def test_load_data_from_json_fails_with_empty_folder(tmp_path):
    env.DASHBOARD_DATA_PATH = tmp_path  # Empty temp directory

    with pytest.raises(FileNotFoundError, match="No JSON files found"):
        load_data.load_data_from_json(env)


def test_load_data_from_json_fails_with_missing_keys(tmp_path):
    # Create a file missing required keys
    broken_file = tmp_path / "broken.json"
    sample = [{
        "date": "2023-01-01T00:00:00",
        "solar_angle": 30,
        # Missing 'red', 'green', 'blue'
    }]
    with open(broken_file, "w") as f:
        json.dump(sample, f)

    env.DASHBOARD_DATA_PATH = tmp_path

    with pytest.raises(ValueError, match="Could not initialize data structures"):
        load_data.load_data_from_json(env)