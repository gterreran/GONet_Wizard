import numpy as np
import pytest

from GONet_Wizard.GONet_utils import GONetFile, GONetFileRaw
from GONet_Wizard.GONet_utils.src.gonet.filetypes import FileType


@pytest.fixture
def compact_raw():
    return GONetFileRaw(
        filename="synthetic.jpg",
        blue=np.array([[1, 2], [3, 4]], dtype=np.uint16),
        green1=np.array([[10, 20], [30, 40]], dtype=np.uint16),
        green2=np.array([[100, 200], [300, 400]], dtype=np.uint16),
        red=np.array([[1000, 2000], [3000, 4000]], dtype=np.uint16),
        meta={"kind": "synthetic"},
        filetype=FileType.SCIENCE,
    )


def test_raw_constructor_casts_channels_and_preserves_metadata(compact_raw):
    assert compact_raw.filename == "synthetic.jpg"
    assert compact_raw.meta == {"kind": "synthetic"}
    assert compact_raw.filetype is FileType.SCIENCE
    assert compact_raw.is_bayer_planes is False

    for channel in compact_raw.CHANNELS:
        assert compact_raw.get_channel(channel).dtype == np.float64


def test_raw_rejects_single_green_channel_access(compact_raw):
    with pytest.raises(AttributeError, match="green1.*green2"):
        _ = compact_raw.green


def test_raw_constructor_validates_inputs():
    arr = np.ones((2, 2))

    with pytest.raises(TypeError, match="filename"):
        GONetFileRaw(123, arr, arr, arr, arr, None, FileType.SCIENCE)

    with pytest.raises(TypeError, match="blue"):
        GONetFileRaw("x.jpg", [[1]], arr, arr, arr, None, FileType.SCIENCE)

    with pytest.raises(ValueError, match="2D"):
        GONetFileRaw("x.jpg", np.ones((2, 2, 1)), arr, arr, arr, None, FileType.SCIENCE)

    with pytest.raises(ValueError, match="must match"):
        GONetFileRaw("x.jpg", np.ones((3, 3)), arr, arr, arr, None, FileType.SCIENCE)

    with pytest.raises(TypeError, match="meta"):
        GONetFileRaw("x.jpg", arr, arr, arr, arr, meta="bad", filetype=FileType.SCIENCE)

    with pytest.raises(TypeError, match="filetype"):
        GONetFileRaw("x.jpg", arr, arr, arr, arr, meta=None, filetype="science")


def test_to_bayer_planes_places_channels_at_bggr_offsets(compact_raw):
    planes = compact_raw.to_bayer_planes(fill_value=-1)

    assert set(planes) == set(compact_raw.CHANNELS)
    for plane in planes.values():
        assert plane.shape == (4, 4)

    expected_blue = np.full((4, 4), -1.0)
    expected_green1 = np.full((4, 4), -1.0)
    expected_green2 = np.full((4, 4), -1.0)
    expected_red = np.full((4, 4), -1.0)

    expected_blue[0::2, 0::2] = compact_raw.blue
    expected_green1[0::2, 1::2] = compact_raw.green1
    expected_green2[1::2, 0::2] = compact_raw.green2
    expected_red[1::2, 1::2] = compact_raw.red

    np.testing.assert_array_equal(planes["blue"], expected_blue)
    np.testing.assert_array_equal(planes["green1"], expected_green1)
    np.testing.assert_array_equal(planes["green2"], expected_green2)
    np.testing.assert_array_equal(planes["red"], expected_red)


def test_as_bayer_planes_inplace_updates_state_and_returns_self(compact_raw):
    returned = compact_raw.as_bayer_planes(inplace=True, fill_value=-1)

    assert returned is compact_raw
    assert compact_raw.is_bayer_planes is True
    assert compact_raw.blue.shape == (4, 4)
    np.testing.assert_array_equal(compact_raw.blue[0::2, 0::2], [[1, 2], [3, 4]])
    assert np.all(compact_raw.blue[0::2, 1::2] == -1)


def test_as_bayer_planes_copy_leaves_original_compact(compact_raw):
    copied = compact_raw.as_bayer_planes(inplace=False, fill_value=-1)

    assert copied is not compact_raw
    assert copied.is_bayer_planes is True
    assert compact_raw.is_bayer_planes is False
    assert compact_raw.blue.shape == (2, 2)
    assert copied.blue.shape == (4, 4)
    assert copied.meta == compact_raw.meta
    assert copied.filetype is compact_raw.filetype


def test_as_compact_quads_round_trips_from_bayer_planes(compact_raw):
    planes = compact_raw.as_bayer_planes(inplace=False, fill_value=np.nan)
    compact = planes.as_compact_quads()

    assert compact.is_bayer_planes is False
    for channel in compact_raw.CHANNELS:
        np.testing.assert_array_equal(
            compact.get_channel(channel),
            compact_raw.get_channel(channel),
        )


def test_as_bayer_planes_and_as_compact_quads_warn_when_no_conversion_needed(compact_raw):
    with pytest.warns(RuntimeWarning, match="already in compact"):
        assert compact_raw.as_compact_quads() is compact_raw

    planes = compact_raw.as_bayer_planes(inplace=False)
    with pytest.warns(RuntimeWarning, match="already in Bayer-plane"):
        assert planes.as_bayer_planes() is planes


def test_raw_scalar_operation_preserves_representation_and_metadata(compact_raw):
    result = compact_raw + 5

    assert isinstance(result, GONetFileRaw)
    assert result.is_bayer_planes is False
    assert result.meta == compact_raw.meta
    assert result.filetype is compact_raw.filetype
    np.testing.assert_array_equal(result.green2, compact_raw.green2 + 5)

    planes = compact_raw.as_bayer_planes(inplace=False, fill_value=0)
    result_planes = planes * 2
    assert result_planes.is_bayer_planes is True
    np.testing.assert_array_equal(result_planes.red, planes.red * 2)


def test_raw_raw_operation_keeps_bayer_representation_when_both_are_bayer(compact_raw):
    left = compact_raw.as_bayer_planes(inplace=False, fill_value=0)
    right = compact_raw.as_bayer_planes(inplace=False, fill_value=0)

    result = left + right

    assert isinstance(result, GONetFileRaw)
    assert result.is_bayer_planes is True
    np.testing.assert_array_equal(result.blue, left.blue + right.blue)


def test_raw_raw_operation_compacts_mixed_representations_with_warning(compact_raw):
    planes = compact_raw.as_bayer_planes(inplace=False, fill_value=0)

    with pytest.warns(RuntimeWarning, match="Auto-converting"):
        result = planes - compact_raw

    assert isinstance(result, GONetFileRaw)
    assert result.is_bayer_planes is False
    np.testing.assert_array_equal(result.red, np.zeros_like(compact_raw.red))


def test_raw_base_operation_averages_greens_and_returns_base_gonetfile(compact_raw):
    base = GONetFile(
        filename="base.tiff",
        blue=np.ones((2, 2)),
        green=np.ones((2, 2)),
        red=np.ones((2, 2)),
        meta=None,
        filetype=FileType.FLAT,
    )

    with pytest.warns(RuntimeWarning, match="averaging green1/green2"):
        result = compact_raw + base

    assert isinstance(result, GONetFile)
    assert not isinstance(result, GONetFileRaw)
    expected_green = 0.5 * (compact_raw.green1 + compact_raw.green2) + base.green
    np.testing.assert_array_equal(result.green, expected_green)
