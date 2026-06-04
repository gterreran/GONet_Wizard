from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def test_version_falls_back_when_distribution_metadata_is_missing(monkeypatch):
    import GONet_Wizard._version as version_mod

    def fake_version(_dist_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", fake_version)
    reloaded = importlib.reload(version_mod)

    assert reloaded.__version__ == "dev"


def test_package_resources_are_available_from_installed_package():
    root = files("GONet_Wizard")

    assert (root / "GONet_utils" / "src" / "data_spec.yaml").is_file()
    assert (root / "gui" / "templates" / "base.html").is_file()
    assert (root / "static" / "css" / "style.css").is_file()
    assert (root / "static" / "img" / "logo" / "GONet_Wizard.ico").is_file()


def test_build_full_array_weight_parser_accepts_comma_pairs():
    from GONet_Wizard.commands.build_full_array import parse_channel_weights

    assert parse_channel_weights(None) is None
    assert parse_channel_weights("red=0.25, green1=0.5,, blue=1") == {
        "red": 0.25,
        "green1": 0.5,
        "blue": 1.0,
    }


@pytest.mark.parametrize("text", ["red", "=1", "red=not-a-number"])
def test_build_full_array_weight_parser_rejects_invalid_entries(text: str):
    from GONet_Wizard.commands.build_full_array import parse_channel_weights

    with pytest.raises(ValueError):
        parse_channel_weights(text)


def test_build_full_array_cli_passes_parsed_weights(monkeypatch, tmp_path: Path):
    import GONet_Wizard.commands.build_full_array as command

    input_file = tmp_path / "image.jpg"
    input_file.write_bytes(b"not actually parsed")
    calls = []

    monkeypatch.setattr(command, "filter_by_ext", lambda paths, exts: [input_file])
    monkeypatch.setattr(command, "build_full_array", lambda **kwargs: calls.append(kwargs))

    args = SimpleNamespace(
        input=[input_file],
        show=False,
        outfile=None,
        verbose=True,
        weights="red=0.25,green1=0.5,green2=0.5,blue=0.25",
    )

    command.cli_handler(args)

    assert len(calls) == 1
    assert calls[0]["gonet_file"] == input_file
    assert calls[0]["channel_weights"] == {
        "red": 0.25,
        "green1": 0.5,
        "green2": 0.5,
        "blue": 0.25,
    }


def test_raw_as_bayer_planes_inplace_returns_self_and_sets_state(small_raw_file):
    raw = small_raw_file
    original_blue = raw.blue.copy()

    returned = raw.as_bayer_planes(inplace=True, fill_value=-1)

    assert returned is raw
    assert raw.is_bayer_planes is True
    assert raw.blue.shape == (original_blue.shape[0] * 2, original_blue.shape[1] * 2)
    np.testing.assert_array_equal(raw.blue[0::2, 0::2], original_blue)


def test_raw_as_bayer_planes_copy_keeps_original_compact(small_raw_file):
    raw = small_raw_file

    expanded = raw.as_bayer_planes(inplace=False, fill_value=-1)

    assert expanded is not raw
    assert expanded.is_bayer_planes is True
    assert raw.is_bayer_planes is False
    assert expanded.red.shape == (raw.red.shape[0] * 2, raw.red.shape[1] * 2)
