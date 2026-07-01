from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from astropy.time import Time
from pathlib import Path

from GONet_Wizard.GONet_utils import DATA_SPEC
from GONet_Wizard.GONet_utils.src.extractors.astro_info import AstroInfo
from GONet_Wizard.GONet_utils.src.extractors.extraction_values import process_single_file
from GONet_Wizard.GONet_utils.src.extractors.file_info import FileInfo
from GONet_Wizard.GONet_utils.src.extractors.shape_info import ShapeInfo
from GONet_Wizard.GONet_utils.src.extractors.time_info import TimeInfo
from GONet_Wizard.GONet_utils.src.extractors.weather_info import WeatherInfo
import GONet_Wizard.GONet_utils.src.extractors.extraction_values as extraction_values_module


def test_file_info_extracts_filename_camera_unix_time_and_context_time():
    files = [
        "/tmp/11_1700000000.jpg",
        "/tmp/nested/12_1700003600.tiff",
    ]

    results, context = FileInfo().extract({"file_list": files}, {})

    assert results["files"] == files
    assert [Path(p) for p in results[DATA_SPEC["filename"].key]] == [
        Path(p) for p in files
    ]
    assert results[DATA_SPEC["camera"].key] == [11, 12]
    assert results[DATA_SPEC["unix_time"].key] == [1700000000, 1700003600]
    np.testing.assert_array_equal(context["time"].unix.astype(int), [1700000000, 1700003600])


def test_file_info_rejects_filenames_without_expected_numeric_parts():
    with pytest.raises(ValueError):
        FileInfo().extract({"file_list": ["not_a_gonet_file.jpg"]}, {})


def test_time_info_extracts_vectorized_time_fields():
    raw = {"file_list": ["1_0.jpg", "1_3600.jpg"]}
    context = {"time": Time([0, 3600], format="unix")}

    results, returned_context = TimeInfo().extract(raw, context)

    assert returned_context is context
    assert results["files"] == raw["file_list"]
    assert results[DATA_SPEC["date_utc"].key][0].startswith("1970-01-01T00:00:00")
    assert list(results[DATA_SPEC["hours_utc"].key]) == ["00:00:00", "01:00:00"]
    np.testing.assert_allclose(results[DATA_SPEC["float_hours_utc"].key], [0.0, 1 / 24])
    assert len(results[DATA_SPEC["date_local"].key]) == 2
    assert len(results[DATA_SPEC["mjd"].key]) == 2


def test_shape_info_extracts_circle_fields_without_changing_context():
    raw = {
        "file_list": ["a.jpg"],
        "extraction_parameters": {
            "shape": "circle",
            "x0": 10,
            "y0": 20,
            "param1": 5,
            "start_angle": 0,
            "end_angle": 90,
        },
    }
    context = {"existing": object()}

    results, returned_context = ShapeInfo().extract(raw, context)

    assert returned_context is context
    assert results["files"] == ["a.jpg"]
    assert results[DATA_SPEC["shape"].key] == "circle"
    assert results[DATA_SPEC["radius"].key] == 5
    assert results[DATA_SPEC["start_angle"].key] == 0
    assert results[DATA_SPEC["end_angle"].key] == 90


def test_shape_info_extracts_rectangle_fields():
    raw = {
        "file_list": ["a.jpg"],
        "extraction_parameters": {
            "shape": "rectangle",
            "x0": 10,
            "y0": 20,
            "param1": 6,
            "param2": 4,
            "start_angle": -180,
            "end_angle": 180,
        },
    }

    results, _ = ShapeInfo().extract(raw, {})

    assert results[DATA_SPEC["shape"].key] == "rectangle"
    assert results[DATA_SPEC["x0"].key] == 10
    assert results[DATA_SPEC["side1"].key] == 6
    assert results[DATA_SPEC["side2"].key] == 4


def test_astro_info_uses_astronomy_helpers(monkeypatch):
    import GONet_Wizard.GONet_utils.src.extractors.astro_info as astro_module

    class FakeCoord:
        def __init__(self, values):
            self.values = np.asarray(values, dtype=float)

        def transform_to(self, altaz):
            return SimpleNamespace(alt=SimpleNamespace(deg=self.values))

    monkeypatch.setattr(astro_module, "EarthLocation", lambda **kwargs: ("location", kwargs))
    monkeypatch.setattr(astro_module, "AltAz", lambda **kwargs: ("altaz", kwargs))
    monkeypatch.setattr(astro_module, "get_sun", lambda time: FakeCoord([1.0, 2.0]))
    monkeypatch.setattr(astro_module, "get_body", lambda body, time: FakeCoord([3.0, 4.0]))
    monkeypatch.setattr(
        astro_module.astroplan.moon,
        "moon_illumination",
        lambda time: np.asarray([0.25, 0.50]),
    )

    raw = {"file_list": ["a.jpg", "b.jpg"]}
    results, context = AstroInfo().extract(raw, {"time": object()})

    assert results["files"] == raw["file_list"]
    np.testing.assert_allclose(results[DATA_SPEC["sunaltaz"].key], [1.0, 2.0])
    np.testing.assert_allclose(results[DATA_SPEC["moonaltaz"].key], [3.0, 4.0])
    np.testing.assert_allclose(results[DATA_SPEC["moon_illumination"].key], [0.25, 0.50])
    assert context["time"] is not None


class FakeHourly:
    def __init__(self, location, start_time, end_time):
        self.location = location
        self.start_time = start_time
        self.end_time = end_time

    def fetch(self):
        return pd.DataFrame(
            {
                "temp": [10.0, 11.0],
                "dwpt": [1.0, 2.0],
                "wspd": [5.0, 6.0],
                "pres": [1000.0, 1001.0],
                "rhum": [70.0, 71.0],
                "coco": [1, 2],
            },
            index=pd.to_datetime([datetime(1970, 1, 1, 0), datetime(1970, 1, 1, 1)]),
        )


def test_weather_info_matches_weather_rows_by_observation_time(monkeypatch):
    import GONet_Wizard.GONet_utils.src.extractors.weather_info as weather_module

    monkeypatch.setattr(weather_module, "Hourly", FakeHourly)
    monkeypatch.setattr(weather_module, "Point", lambda *args, **kwargs: (args, kwargs))

    raw = {"file_list": ["a.jpg", "b.jpg"]}
    context = {"time": Time([0, 3600], format="unix")}

    results, returned_context = WeatherInfo().extract(raw, context)

    assert returned_context is context
    assert results["files"] == raw["file_list"]
    np.testing.assert_allclose(results[DATA_SPEC["temperature"].key], [10.0, 11.0])
    np.testing.assert_allclose(results[DATA_SPEC["dew_point"].key], [1.0, 2.0])
    np.testing.assert_array_equal(results[DATA_SPEC["condition_code"].key], [1, 2])


def test_weather_info_returns_nan_arrays_when_no_weather_data(monkeypatch):
    import GONet_Wizard.GONet_utils.src.extractors.weather_info as weather_module

    class EmptyHourly(FakeHourly):
        def fetch(self):
            return pd.DataFrame()

    monkeypatch.setattr(weather_module, "Hourly", EmptyHourly)
    monkeypatch.setattr(weather_module, "Point", lambda *args, **kwargs: (args, kwargs))

    raw = {"file_list": ["a.jpg", "b.jpg"]}
    context = {"time": Time([0, 3600], format="unix")}

    results, _ = WeatherInfo().extract(raw, context)

    assert results["files"] == raw["file_list"]
    assert np.isnan(results[DATA_SPEC["temperature"].key]).all()
    assert np.isnan(results[DATA_SPEC["condition_code"].key]).all()


class FakeGONetFile:
    def __init__(self):
        self.meta = {"exposure_time": 30.0}
        self.red = np.arange(25, dtype=float).reshape(5, 5)
        self.green = self.red + 100

    def remove_overscan(self):
        self.overscan_removed = True

    def get_channel(self, channel):
        return getattr(self, channel)


def test_process_single_file_extracts_requested_channels(monkeypatch):
    import GONet_Wizard.GONet_utils.src.extractors.extraction_values as extraction_module

    monkeypatch.setattr(
        extraction_module.GONetFile,
        "from_file",
        staticmethod(lambda filename: FakeGONetFile()),
    )

    result = process_single_file(
        "fake.jpg",
        channels=["red", "green"],
        extraction_params={
            "shape": "circle",
            "x0": 2,
            "y0": 2,
            "param1": 1,
            "start_angle": -180,
            "end_angle": 180,
        },
    )

    assert result["files"] == "fake.jpg"
    assert result[DATA_SPEC["exptime"].key] == 30.0
    assert result["red"][DATA_SPEC["npixels"].key] == 5
    assert result["red"][DATA_SPEC["total_counts"].key] == pytest.approx(60.0)
    assert result["green"][DATA_SPEC["total_counts"].key] == pytest.approx(560.0)


def test_process_single_file_returns_none_when_file_loading_fails(monkeypatch):
    import GONet_Wizard.GONet_utils.src.extractors.extraction_values as extraction_module

    def raise_error(filename):
        raise RuntimeError("boom")

    monkeypatch.setattr(extraction_module.GONetFile, "from_file", staticmethod(raise_error))

    result = process_single_file(
        "bad.jpg",
        channels=["red"],
        extraction_params={
            "shape": "circle",
            "x0": 2,
            "y0": 2,
            "param1": 1,
            "start_angle": -180,
            "end_angle": 180,
        },
    )

    assert result is None


def test_extraction_executor_defaults_to_thread_in_frozen_app(monkeypatch):
    monkeypatch.setattr(extraction_values_module.sys, "frozen", True, raising=False)
    monkeypatch.delenv(extraction_values_module._EXECUTOR_ENV_VAR, raising=False)

    assert extraction_values_module._executor_mode() == "thread"


def test_extraction_executor_defaults_to_process_in_source_mode(monkeypatch):
    monkeypatch.delattr(extraction_values_module.sys, "frozen", raising=False)
    monkeypatch.delenv(extraction_values_module._EXECUTOR_ENV_VAR, raising=False)

    assert extraction_values_module._executor_mode() == "process"


def test_extraction_executor_env_override(monkeypatch):
    monkeypatch.setattr(extraction_values_module.sys, "frozen", True, raising=False)
    monkeypatch.setenv(extraction_values_module._EXECUTOR_ENV_VAR, "serial")

    assert extraction_values_module._executor_mode() == "serial"
