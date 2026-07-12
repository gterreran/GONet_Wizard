from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import GONet_Wizard.commands.split_raw as split_raw


class FakeGONetFile:
    loaded: list[Path] = []
    written_tiffs: list[tuple[str, bool]] = []
    written_jpegs: list[tuple[str, bool]] = []

    @classmethod
    def reset(cls) -> None:
        cls.loaded = []
        cls.written_tiffs = []
        cls.written_jpegs = []

    @classmethod
    def from_file(cls, path):
        cls.loaded.append(Path(path))
        return cls()

    def write_to_tiff(self, path, white_balance=True):
        self.written_tiffs.append((str(path), white_balance))
        Path(path).write_text("tiff")

    def write_to_jpeg(self, path, white_balance=True):
        self.written_jpegs.append((str(path), white_balance))
        Path(path).write_text("jpeg")


@pytest.fixture(autouse=True)
def fake_gonet_file(monkeypatch):
    FakeGONetFile.reset()
    monkeypatch.setattr(split_raw, "GONetFile", FakeGONetFile)
    return FakeGONetFile


def test_output_paths_default_next_to_input_with_safe_jpeg_suffix(tmp_path: Path):
    raw = tmp_path / "image.jpg"

    paths = split_raw.output_paths_for_raw(raw)

    assert paths.input_file == raw
    assert paths.tiff == tmp_path / "image.tiff"
    assert paths.jpeg == tmp_path / "image.jpeg"


def test_split_raw_file_writes_tiff_and_jpeg_by_default(tmp_path: Path):
    raw = tmp_path / "image.jpg"
    raw.write_text("raw")

    outputs = split_raw.split_raw_file(raw)

    assert outputs.tiff == tmp_path / "image.tiff"
    assert outputs.jpeg == tmp_path / "image.jpeg"
    assert FakeGONetFile.loaded == [raw]
    assert FakeGONetFile.written_tiffs == [(str(tmp_path / "image.tiff"), False)]
    assert FakeGONetFile.written_jpegs == [(str(tmp_path / "image.jpeg"), True)]


def test_output_paths_use_product_subfolders_when_outdir_is_set(tmp_path: Path):
    raw = tmp_path / "image.jpg"
    outdir = tmp_path / "converted"

    paths = split_raw.output_paths_for_raw(raw, outdir=outdir)

    assert paths.tiff == outdir / "tiffs" / "image.tiff"
    assert paths.jpeg == outdir / "jpegs" / "image.jpeg"


def test_split_raw_file_can_apply_tiff_white_balance(tmp_path: Path):
    raw = tmp_path / "image.jpg"
    raw.write_text("raw")

    split_raw.split_raw_file(raw, output_format="tiff", tiff_white_balance=True)

    assert FakeGONetFile.written_tiffs == [(str(tmp_path / "image.tiff"), True)]
    assert FakeGONetFile.written_jpegs == []


def test_split_raw_file_can_write_only_jpeg_without_white_balance(tmp_path: Path):
    raw = tmp_path / "image.jpg"
    raw.write_text("raw")
    outdir = tmp_path / "converted"

    outputs = split_raw.split_raw_file(
        raw,
        outdir=outdir,
        output_format="jpeg",
        jpeg_white_balance=False,
    )

    assert outputs.tiff is None
    assert outputs.jpeg == outdir / "jpegs" / "image.jpeg"
    assert FakeGONetFile.written_tiffs == []
    assert FakeGONetFile.written_jpegs == [(str(outdir / "jpegs" / "image.jpeg"), False)]


def test_split_raw_file_refuses_existing_output_without_overwrite(tmp_path: Path):
    raw = tmp_path / "image.jpg"
    raw.write_text("raw")
    (tmp_path / "image.tiff").write_text("old")

    with pytest.raises(FileExistsError, match="Use --overwrite"):
        split_raw.split_raw_file(raw)

    assert FakeGONetFile.loaded == []


def test_cli_handler_filters_inputs_and_passes_options(monkeypatch, tmp_path: Path, capsys):
    raw = tmp_path / "image.jpg"
    raw.write_text("raw")
    ignored = tmp_path / "notes.txt"
    ignored.write_text("ignore")
    calls = []

    def fake_split_raw_files(**kwargs):
        calls.append(kwargs)
        return [
            split_raw.SplitRawOutput(
                input_file=raw,
                tiff=None,
                jpeg=tmp_path / "out" / "jpegs" / "image.jpeg",
            )
        ]

    monkeypatch.setattr(split_raw, "split_raw_files", fake_split_raw_files)

    args = SimpleNamespace(
        input=[raw, ignored],
        outdir=str(tmp_path / "out"),
        format="jpeg",
        overwrite=True,
        tiff_white_balance=True,
        no_jpeg_white_balance=True,
    )

    summary = split_raw.cli_handler(args)
    captured = capsys.readouterr()

    assert calls == [
        {
            "input_files": [raw],
            "outdir": str(tmp_path / "out"),
            "output_format": "jpeg",
            "overwrite": True,
            "tiff_white_balance": True,
            "jpeg_white_balance": False,
        }
    ]
    assert summary is None
    assert str(tmp_path / "out" / "jpegs" / "image.jpeg") in captured.out
