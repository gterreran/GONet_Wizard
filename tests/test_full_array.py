from pathlib import Path

import numpy as np
import pytest

from GONet_Wizard.GONet_utils import GONetFileRaw
from GONet_Wizard.GONet_utils.src.gonet.analysis_utils import full_array
from GONet_Wizard.GONet_utils.src.gonet.filetypes import FileType


@pytest.fixture
def compact_raw_for_full_array():
    raw = GONetFileRaw(
        filename="synthetic.jpg",
        blue=np.array([[1, 2], [3, 4]], dtype=float),
        green1=np.array([[10, 20], [30, 40]], dtype=float),
        green2=np.array([[100, 200], [300, 400]], dtype=float),
        red=np.array([[1000, 2000], [3000, 4000]], dtype=float),
        meta=None,
        filetype=FileType.SCIENCE,
    )

    # The production function removes real-camera overscan rows.  These tiny
    # synthetic arrays intentionally bypass that step so the test isolates the
    # full-array assembly logic.
    raw.remove_overscan = lambda: None
    return raw


def test_hist_match_to_ref_preserves_shape_and_dtype():
    src = np.array([[0, 1], [2, 3]], dtype=np.float64)
    ref = np.array([[10, 11], [12, 13]], dtype=np.float64)

    matched = full_array.hist_match_to_ref(src, ref, n_bins=8)

    assert matched.shape == src.shape
    assert matched.dtype == np.float32
    assert np.all(np.isfinite(matched))


def test_hist_match_to_ref_constant_image_returns_source_as_float32():
    src = np.full((3, 3), 7.0)
    ref = np.full((3, 3), 7.0)

    matched = full_array.hist_match_to_ref(src, ref)

    assert matched.dtype == np.float32
    np.testing.assert_array_equal(matched, src.astype(np.float32))


def test_hist_match_to_ref_raises_when_clip_removes_all_values():
    src = np.array([1, 2, 3], dtype=float)
    ref = np.array([4, 5, 6], dtype=float)

    with pytest.raises(ValueError, match="No finite values"):
        full_array.hist_match_to_ref(src, ref, clip=(100, 200))


def test_hist_payload_ignores_nonfinite_values():
    centers, density = full_array._hist_payload(
        np.array([0.0, 1.0, np.nan, np.inf]),
        hist_bins=2,
    )

    assert centers.dtype == np.float32
    assert density.dtype == np.float32
    assert len(centers) == 2
    assert len(density) == 2
    assert np.all(np.isfinite(centers))
    assert np.all(np.isfinite(density))


def test_hist_payload_returns_empty_arrays_for_no_finite_values():
    centers, density = full_array._hist_payload(np.array([np.nan, np.inf]))

    assert centers.dtype == np.float32
    assert density.dtype == np.float32
    assert centers.size == 0
    assert density.size == 0


def test_combine_channels_weighted_ignores_nan_per_pixel():
    matched = {
        "blue": np.array([[1.0, np.nan], [3.0, 4.0]]),
        "green1": np.array([[10.0, 20.0], [np.nan, 40.0]]),
    }

    combined = full_array._combine_channels_weighted(
        matched=matched,
        channel_order=["blue", "green1"],
        channel_weights={"blue": 1.0, "green1": 3.0},
    )

    expected = np.array(
        [
            [(1.0 + 3.0 * 10.0) / 4.0, 20.0],
            [3.0, (4.0 + 3.0 * 40.0) / 4.0],
        ],
        dtype=np.float32,
    )

    assert combined.dtype == np.float32
    np.testing.assert_allclose(combined, expected)


def test_build_full_array_rejects_non_jpg_input(tmp_path):
    with pytest.raises(ValueError, match="RAW .jpg"):
        full_array.build_full_array(tmp_path / "not_raw.tiff")


def test_build_full_array_saves_image_and_optional_diagnostics(
    tmp_path,
    monkeypatch,
    compact_raw_for_full_array,
):
    outfile = tmp_path / "full_array.npz"

    monkeypatch.setattr(
        full_array.GONetFileRaw,
        "from_file",
        classmethod(lambda cls, path, meta=False: compact_raw_for_full_array),
    )
    monkeypatch.setattr(
        full_array,
        "hist_match_to_ref",
        lambda src, ref, n_bins=512, clip=None: np.asarray(src, dtype=np.float32),
    )

    full_array.build_full_array(
        gonet_file=Path("synthetic.jpg"),
        outfile=outfile,
        channel_weights={"blue": 1.0, "green1": 1.0, "green2": 1.0, "red": 1.0},
        save_diagnostics=True,
        hist_bins=4,
    )

    assert outfile.exists()
    with np.load(outfile) as data:
        assert data["image"].shape == (4, 4)
        assert data["image"].dtype == np.float32
        assert "raw_hist_bins_blue" in data.files
        assert "matched_hist_density_red" in data.files

        image = data["image"]
        assert image[0, 0] == pytest.approx(1.0)      # blue CFA location
        assert image[0, 1] == pytest.approx(10.0)     # green1 CFA location
        assert image[1, 0] == pytest.approx(100.0)    # green2 CFA location
        assert image[1, 1] == pytest.approx(1000.0)   # red CFA location


def test_build_full_array_can_skip_diagnostics(tmp_path, monkeypatch, compact_raw_for_full_array):
    outfile = tmp_path / "full_array_no_diag.npz"

    monkeypatch.setattr(
        full_array.GONetFileRaw,
        "from_file",
        classmethod(lambda cls, path, meta=False: compact_raw_for_full_array),
    )
    monkeypatch.setattr(
        full_array,
        "hist_match_to_ref",
        lambda src, ref, n_bins=512, clip=None: np.asarray(src, dtype=np.float32),
    )

    full_array.build_full_array(
        gonet_file=Path("synthetic.jpg"),
        outfile=outfile,
        save_diagnostics=False,
    )

    with np.load(outfile) as data:
        assert data.files == ["image"]
        assert data["image"].shape == (4, 4)
