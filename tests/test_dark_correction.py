import numpy as np
import pytest

from GONet_Wizard.GONet_utils.src.gonet.analysis_utils.dark_correction import (
    remove_overscan,
)


class FakeGONetFile:
    CHANNELS = ["blue", "green", "red"]

    def __init__(self, filename, blue, green, red, meta=None, filetype="fake"):
        self.filename = filename
        self.blue = blue
        self.green = green
        self.red = red
        self.meta = meta or {}
        self.filetype = filetype

    def get_channel(self, channel):
        return getattr(self, channel)

    def set_channel(self, channel, data, check_shape=True):
        setattr(self, channel, data)


class FakeGONetFileRaw:
    CHANNELS = ["blue", "green1", "green2", "red"]

    def __init__(
        self,
        filename,
        blue,
        green1,
        green2,
        red,
        meta=None,
        filetype="fake-raw",
        is_bayer_planes=False,
    ):
        self.filename = filename
        self.blue = blue
        self.green1 = green1
        self.green2 = green2
        self.red = red
        self.meta = meta or {}
        self.filetype = filetype
        self.is_bayer_planes = is_bayer_planes

    def get_channel(self, channel):
        return getattr(self, channel)

    def set_channel(self, channel, data, check_shape=True):
        setattr(self, channel, data)


def make_channel(value, overscan_value):
    data = np.full((30, 4), value, dtype=float)
    data[10:20] = overscan_value
    return data


def test_remove_overscan_inplace_updates_selected_channels_only():
    blue = make_channel(20, 5)
    green = make_channel(100, 10)
    red = make_channel(200, 20)
    obj = FakeGONetFile("image.tiff", blue.copy(), green.copy(), red.copy())

    returned = remove_overscan(obj, inplace=True, channels=["blue", "red"])

    assert returned is None
    np.testing.assert_allclose(obj.blue, blue - 5)
    np.testing.assert_allclose(obj.red, red - 20)
    np.testing.assert_allclose(obj.green, green)


def test_remove_overscan_non_inplace_returns_same_class_and_preserves_metadata():
    blue = make_channel(20, 5)
    green = make_channel(100, 10)
    red = make_channel(200, 20)
    meta = {"camera": "GONet"}
    obj = FakeGONetFile("image.tiff", blue.copy(), green.copy(), red.copy(), meta=meta)

    corrected = remove_overscan(obj, inplace=False, channels=["green"])

    assert isinstance(corrected, FakeGONetFile)
    assert corrected is not obj
    assert corrected.filename == "image.tiff"
    assert corrected.meta is meta
    assert corrected.filetype == "fake"
    np.testing.assert_allclose(corrected.green, green - 10)
    np.testing.assert_allclose(corrected.blue, blue)
    np.testing.assert_allclose(corrected.red, red)
    np.testing.assert_allclose(obj.green, green)


def test_remove_overscan_defaults_to_all_declared_channels():
    obj = FakeGONetFile(
        "image.tiff",
        make_channel(20, 5),
        make_channel(100, 10),
        make_channel(200, 20),
    )

    remove_overscan(obj)

    np.testing.assert_allclose(obj.blue[0], np.full(4, 15.0))
    np.testing.assert_allclose(obj.green[0], np.full(4, 90.0))
    np.testing.assert_allclose(obj.red[0], np.full(4, 180.0))


def test_remove_overscan_rejects_invalid_channels():
    obj = FakeGONetFile(
        "image.tiff",
        make_channel(20, 5),
        make_channel(100, 10),
        make_channel(200, 20),
    )

    with pytest.raises(ValueError, match="Invalid channel"):
        remove_overscan(obj, channels=["infrared"])


def test_remove_overscan_preserves_raw_bayer_state_when_copying():
    obj = FakeGONetFileRaw(
        "raw.tiff",
        blue=make_channel(20, 5),
        green1=make_channel(100, 10),
        green2=make_channel(110, 11),
        red=make_channel(200, 20),
        is_bayer_planes=True,
    )

    corrected = remove_overscan(obj, inplace=False, channels=["green1"])

    assert isinstance(corrected, FakeGONetFileRaw)
    assert corrected.is_bayer_planes is True
    np.testing.assert_allclose(corrected.green1, obj.green1 - 10)
    np.testing.assert_allclose(corrected.green2, obj.green2)
