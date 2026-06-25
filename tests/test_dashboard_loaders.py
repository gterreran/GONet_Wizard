from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from GONet_Wizard.GONet_dashboard.src.hood.loaders.base import get_loader
from GONet_Wizard.GONet_dashboard.src.hood.loaders.schema import as_bool, as_datetime, as_float, as_int, parse_hours_of_the_day


def test_schema_coercers_return_none_for_invalid_values():
    assert as_float("1.25") == 1.25
    assert as_float("bad") is None
    assert as_int("3") == 3
    assert as_int("3.5") is None
    assert as_bool("yes") is True
    assert as_bool("off") is False
    assert as_bool("maybe") is None
    assert as_datetime("2026-01-02T03:04:05") == datetime(2026, 1, 2, 3, 4, 5)
    assert as_datetime("not-a-date") is None


def test_parse_hours_of_the_day_wraps_around_day_boundary():
    import datetime as dt

    boundary = dt.time(18, 0, 0)

    assert parse_hours_of_the_day("19:00:00", boundary).date().isoformat() == "2025-01-01"
    assert parse_hours_of_the_day("17:00:00", boundary).date().isoformat() == "2025-01-02"


def test_get_loader_by_name_and_extension():
    assert get_loader("json", Path("anything.dat")).name == "json"
    assert get_loader("csv", Path("anything.dat")).name == "csv"
    assert get_loader(None, Path("data.json")).name == "json"
    assert get_loader(None, Path("data.csv")).name == "csv"

    with pytest.raises(ValueError):
        get_loader("missing", Path("data.json"))

    with pytest.raises(ValueError):
        get_loader(None, Path("data.unknown"))


def test_json_loader_flattens_epoch_channel_records(tmp_path: Path):
    payload = [
        {
            "filepath": "file-a.jpg",
            "local_time": "20:00:00",
            "red": {"mean_counts": "10.5", "npixels": "4"},
            "blue": {"mean_counts": "5.5", "npixels": "4"},
        }
    ]
    fp = tmp_path / "data.json"
    fp.write_text(json.dumps(payload), encoding="utf-8")

    df = get_loader("json", fp).load([fp])

    assert set(df["channel"]) == {"red", "blue"}
    assert set(df["mean_counts"]) == {10.5, 5.5}
    assert set(df["npixels"]) == {4}
    assert set(df["filepath"]) == {"file-a.jpg"}


def test_csv_loader_unpivots_channel_prefixed_columns(tmp_path: Path):
    fp = tmp_path / "data.csv"
    pd.DataFrame(
        [
            {
                "filepath": "file-a.jpg",
                "red_mean_counts": "10",
                "red_npixels": "2",
                "green_mean_counts": "20",
                "green_npixels": "2",
            }
        ]
    ).to_csv(fp, index=False)

    df = get_loader("csv", fp).load([fp])

    assert set(df["channel"]) == {"red", "green"}
    assert set(df["mean_counts"]) == {10.0, 20.0}
    assert set(df["npixels"]) == {2}
