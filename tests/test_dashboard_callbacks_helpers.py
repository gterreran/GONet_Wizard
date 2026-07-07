"""Regression tests for dashboard export and status serialization helpers."""

import datetime
import json

import numpy as np
import pandas as pd

from GONet_Wizard.GONet_dashboard.src.callbacks import (
    _build_export_records,
    _build_status_dict,
)


def _component_id(component_type, index):
    return {"type": component_type, "index": index}


def test_build_export_records_uses_data_spec_field_categories():
    """Exports should derive environment/channel fields from DATA_SPEC."""
    df = pd.DataFrame(
        [
            {
                "epoch_idx": 0,
                "filename": "image.jpg",
                "channel": "red",
                "camera": np.int64(1),
                "date_utc": datetime.datetime(2026, 7, 7, 12, 0),
                "mean_counts": np.float64(12.5),
                "std": np.float64(np.nan),
            },
            {
                "epoch_idx": 0,
                "filename": "image.jpg",
                "channel": "green",
                "camera": np.int64(1),
                "date_utc": datetime.datetime(2026, 7, 7, 12, 0),
                "mean_counts": np.float64(10.0),
                "std": np.float64(0.25),
            },
        ]
    )

    records = _build_export_records(df, [0, 999])

    assert records == [
        {
            "filename": "image.jpg",
            "camera": 1,
            "date_utc": "2026-07-07T12:00:00",
            "red": {"mean_counts": 12.5, "std": None},
            "green": {"mean_counts": 10.0, "std": 0.25},
            "blue": {"mean_counts": None, "std": None},
        }
    ]


def test_build_export_records_does_not_rescan_epochs(monkeypatch):
    """Export should select requested epochs once, not once per record."""
    rows = []
    for epoch_idx in range(100):
        for channel in ("red", "green", "blue"):
            rows.append(
                {
                    "epoch_idx": epoch_idx,
                    "filename": f"image-{epoch_idx}.jpg",
                    "channel": channel,
                    "camera": 1,
                    "mean_counts": float(epoch_idx),
                }
            )
    df = pd.DataFrame(rows)

    original_eq = pd.Series.__eq__
    epoch_equality_scans = []

    def tracked_eq(series, other):
        if series.name == "epoch_idx":
            epoch_equality_scans.append(other)
        return original_eq(series, other)

    monkeypatch.setattr(pd.Series, "__eq__", tracked_eq)

    records = _build_export_records(df, list(range(100)))

    assert len(records) == 100
    assert epoch_equality_scans == []


def test_build_status_dict_groups_mixed_type_filter_ids_without_comparing_them():
    """Current string IDs and legacy integer IDs can coexist safely."""
    current_index = "0|4f573332-fab2-4b9c-bfab-6103f57be68f"
    legacy_index = 1
    args = (
        "x-axis-dropdown",
        "date_local",
        "y-axis-dropdown",
        "mean_counts",
        [
            _component_id("filter-switch", current_index),
            _component_id("filter-switch", legacy_index),
        ],
        [True, False],
        [
            _component_id("filter-dropdown", current_index),
            _component_id("filter-dropdown", legacy_index),
        ],
        ["temperature", "humidity"],
        [
            _component_id("filter-operator", current_index),
            _component_id("filter-operator", legacy_index),
        ],
        ["<=", ">"],
        [
            _component_id("filter-value", current_index),
            _component_id("filter-value", legacy_index),
        ],
        [0, "80"],
        [_component_id("second-filter-dropdown", current_index)],
        ["pressure"],
        [_component_id("second-filter-operator", current_index)],
        [">="],
        [_component_id("second-filter-value", current_index)],
        [1000],
        "channels",
        ["red", "green"],
    )

    status = _build_status_dict(args)

    assert status["x-axis-dropdown"] == "date_local"
    assert status["channels"] == ["red", "green"]
    assert status["filters"] == [
        {
            "secondary": {
                "second-filter-dropdown": "pressure",
                "second-filter-operator": ">=",
                "second-filter-value": 1000,
            },
            "filter-switch": True,
            "filter-dropdown": "temperature",
            "filter-operator": "<=",
            "filter-value": 0,
        },
        {
            "secondary": {},
            "filter-switch": False,
            "filter-dropdown": "humidity",
            "filter-operator": ">",
            "filter-value": "80",
        },
    ]


def test_build_status_dict_preserves_selection_filter_data():
    """Selection filters should round-trip through saved dashboard status."""
    index = "2|selection-uuid"
    args = (
        [_component_id("filter-switch", index)],
        [True],
        [_component_id("filter-dropdown", index)],
        ["Selection 2"],
        [_component_id("filter-operator", index)],
        ["in"],
        [_component_id("filter-selection-data", index)],
        [[3, 8, 13]],
    )

    status = _build_status_dict(args)

    assert status["filters"] == [
        {
            "secondary": {},
            "filter-switch": True,
            "filter-dropdown": "Selection 2",
            "filter-operator": "in",
            "filter-selection-data": [3, 8, 13],
        }
    ]


def test_load_status_restores_value_and_selection_filters():
    """Saved filters should rebuild with internally consistent component IDs."""
    import base64
    import json

    from GONet_Wizard.GONet_dashboard.src.callbacks import load_status

    status = {
        "x-axis-dropdown": "date_local",
        "y-axis-dropdown": "mean_counts",
        "channels": ["red", "blue"],
        "show-filtered-data-switch": False,
        "filters": [
            {
                "secondary": {
                    "second-filter-dropdown": "pressure",
                    "second-filter-operator": ">=",
                    "second-filter-value": 1000,
                },
                "filter-switch": True,
                "filter-dropdown": "temperature",
                "filter-operator": "<=",
                "filter-value": 0,
            },
            {
                "secondary": {},
                "filter-switch": True,
                "filter-dropdown": "Selection 1",
                "filter-operator": "out",
                "filter-selection-data": [2, 5, 9],
            },
        ],
    }
    encoded = base64.b64encode(json.dumps(status).encode("utf-8")).decode("ascii")
    contents = f"data:application/json;base64,{encoded}"
    labels = [
        {"label": "temperature", "value": "temperature"},
        {"label": "pressure", "value": "pressure"},
    ]

    x_axis, y_axis, channels, show_filtered, filters = load_status.__wrapped__(
        contents, [], labels
    )

    assert (x_axis, y_axis, channels, show_filtered) == (
        "date_local",
        "mean_counts",
        ["red", "blue"],
        False,
    )
    assert len(filters) == 2

    value_filter = filters[0]
    value_index = value_filter.id["index"]
    value_row = value_filter.children[0].children
    assert value_row[0].children.on is True
    assert value_row[1].value == "temperature"
    assert value_row[2].value == "<="
    assert value_row[3].value == 0
    secondary_row = value_filter.children[1].children
    assert secondary_row[1].id["index"] == value_index
    assert secondary_row[1].value == "pressure"
    assert secondary_row[2].value == ">="
    assert secondary_row[3].value == 1000

    selection_filter = filters[1]
    selection_row = selection_filter.children[0].children
    assert selection_row[0].children.on is True
    assert selection_row[2].data == [2, 5, 9]
    assert selection_row[3].value == "out"


def test_export_data_stages_records_for_shared_save_dialog(monkeypatch):
    """Export should return a small descriptor for a one-time JSON payload."""
    from GONet_Wizard.GONet_dashboard.src import callbacks
    from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import (
        _consume_staged_json,
    )

    df = pd.DataFrame(
        [
            {
                "epoch_idx": 0,
                "filename": "image.jpg",
                "channel": "red",
                "camera": 1,
                "mean_counts": 12.5,
            }
        ]
    )
    monkeypatch.setitem(callbacks.app.server.config, "data", df)
    descriptor = callbacks.export_data.__wrapped__(
        {"request_id": 1, "epoch_indices": [0]}
    )

    assert descriptor["filename"] == "filtered_data.json"
    assert descriptor["token"]
    assert descriptor["url"].endswith(descriptor["token"])
    assert set(descriptor) == {"token", "url", "filename"}

    payload, filename = _consume_staged_json(descriptor["token"])
    assert filename == "filtered_data.json"
    assert json.loads(payload) == [
        {
            "filename": "image.jpg",
            "camera": 1,
            "red": {"mean_counts": 12.5},
            "green": {"mean_counts": None},
            "blue": {"mean_counts": None},
        }
    ]

    # Staged URLs are deliberately one-time so large payloads are released as
    # soon as the save flow consumes them.
    assert _consume_staged_json(descriptor["token"]) is None
