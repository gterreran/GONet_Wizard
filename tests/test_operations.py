import numpy as np
import pytest
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_utils.src.gonetfile import FileType
@pytest.fixture
def fake_gonetfile() -> GONetFile:
    """Create a small fake GONetFile for scalar operations."""
    shape = (4, 4)
    red = np.ones(shape) * 100
    green = np.ones(shape) * 200
    blue = np.ones(shape) * 300
    meta = {"dummy": True}
    return GONetFile(
        filename="fake",
        red=red,
        green=green,
        blue=blue,
        meta=meta,
        filetype=FileType.SCIENCE
    )

@pytest.fixture
def other_gonetfile() -> GONetFile:
    """Create a second fake GONetFile for GONet-to-GONet operations."""
    shape = (4, 4)
    red = np.ones(shape) * 2
    green = np.ones(shape) * 3
    blue = np.ones(shape) * 4
    return GONetFile(
        filename="other",
        red=red,
        green=green,
        blue=blue,
        meta=None,
        filetype=None
    )

def test_add_scalar(fake_gonetfile):
    result = fake_gonetfile + 10
    np.testing.assert_array_equal(result.red, fake_gonetfile.red + 10)
    np.testing.assert_array_equal(result.green, fake_gonetfile.green + 10)
    np.testing.assert_array_equal(result.blue, fake_gonetfile.blue + 10)
    assert result.meta == fake_gonetfile.meta
    assert result.filetype == fake_gonetfile.filetype
    assert result.filename == fake_gonetfile.filename

def test_add_gonetfile(fake_gonetfile, other_gonetfile):
    result = fake_gonetfile + other_gonetfile
    np.testing.assert_array_equal(result.red, fake_gonetfile.red + other_gonetfile.red)
    np.testing.assert_array_equal(result.green, fake_gonetfile.green + other_gonetfile.green)
    np.testing.assert_array_equal(result.blue, fake_gonetfile.blue + other_gonetfile.blue)
    assert result.meta is None
    assert result.filetype is None
    assert result.filename is None

def test_mul_scalar(fake_gonetfile):
    result = fake_gonetfile * 2
    np.testing.assert_array_equal(result.red, fake_gonetfile.red * 2)
    np.testing.assert_array_equal(result.green, fake_gonetfile.green * 2)
    np.testing.assert_array_equal(result.blue, fake_gonetfile.blue * 2)
    assert result.meta == fake_gonetfile.meta
    assert result.filetype == fake_gonetfile.filetype
    assert result.filename == fake_gonetfile.filename

def test_mul_gonetfile(fake_gonetfile, other_gonetfile):
    result = fake_gonetfile * other_gonetfile
    np.testing.assert_array_equal(result.red, fake_gonetfile.red * other_gonetfile.red)
    np.testing.assert_array_equal(result.green, fake_gonetfile.green * other_gonetfile.green)
    np.testing.assert_array_equal(result.blue, fake_gonetfile.blue * other_gonetfile.blue)
    assert result.meta is None
    assert result.filetype is None
    assert result.filename is None

def test_sub_scalar(fake_gonetfile):
    result = fake_gonetfile - 50
    np.testing.assert_array_equal(result.red, fake_gonetfile.red - 50)
    np.testing.assert_array_equal(result.green, fake_gonetfile.green - 50)
    np.testing.assert_array_equal(result.blue, fake_gonetfile.blue - 50)
    assert result.meta == fake_gonetfile.meta
    assert result.filetype == fake_gonetfile.filetype
    assert result.filename == fake_gonetfile.filename

def test_sub_gonetfile(fake_gonetfile, other_gonetfile):
    result = fake_gonetfile - other_gonetfile
    np.testing.assert_array_equal(result.red, fake_gonetfile.red - other_gonetfile.red)
    np.testing.assert_array_equal(result.green, fake_gonetfile.green - other_gonetfile.green)
    np.testing.assert_array_equal(result.blue, fake_gonetfile.blue - other_gonetfile.blue)
    assert result.meta is None
    assert result.filetype is None
    assert result.filename is None

def test_div_scalar(fake_gonetfile):
    result = fake_gonetfile / 10
    np.testing.assert_array_almost_equal(result.red, fake_gonetfile.red / 10)
    np.testing.assert_array_almost_equal(result.green, fake_gonetfile.green / 10)
    np.testing.assert_array_almost_equal(result.blue, fake_gonetfile.blue / 10)
    assert result.meta == fake_gonetfile.meta
    assert result.filetype == fake_gonetfile.filetype
    assert result.filename == fake_gonetfile.filename

def test_div_gonetfile(fake_gonetfile, other_gonetfile):
    result = fake_gonetfile / other_gonetfile
    np.testing.assert_array_almost_equal(result.red, fake_gonetfile.red / other_gonetfile.red)
    np.testing.assert_array_almost_equal(result.green, fake_gonetfile.green / other_gonetfile.green)
    np.testing.assert_array_almost_equal(result.blue, fake_gonetfile.blue / other_gonetfile.blue)
    assert result.meta is None
    assert result.filetype is None
    assert result.filename is None

def test_inplace_addition_scalar(fake_gonetfile):
    original_red = fake_gonetfile.red.copy()
    original_green = fake_gonetfile.green.copy()
    original_blue = fake_gonetfile.blue.copy()

    fake_gonetfile += 5

    np.testing.assert_array_equal(fake_gonetfile.red, original_red + 5)
    np.testing.assert_array_equal(fake_gonetfile.green, original_green + 5)
    np.testing.assert_array_equal(fake_gonetfile.blue, original_blue + 5)

    assert fake_gonetfile.meta == {"dummy": True}
    assert fake_gonetfile.filetype == FileType.SCIENCE
    assert fake_gonetfile.filename == "fake"

def test_inplace_addition_gonetfile(fake_gonetfile, other_gonetfile):
    red_before = fake_gonetfile.red.copy()
    green_before = fake_gonetfile.green.copy()
    blue_before = fake_gonetfile.blue.copy()

    fake_gonetfile += other_gonetfile

    np.testing.assert_array_equal(fake_gonetfile.red, red_before + other_gonetfile.red)
    np.testing.assert_array_equal(fake_gonetfile.green, green_before + other_gonetfile.green)
    np.testing.assert_array_equal(fake_gonetfile.blue, blue_before + other_gonetfile.blue)
    assert fake_gonetfile.meta is None
    assert fake_gonetfile.filetype is None
    assert fake_gonetfile.filename is None

def test_invalid_operation_raises(fake_gonetfile):
    with pytest.raises(TypeError):
        _ = fake_gonetfile + "invalid"

def test_breaks_16bit_range(fake_gonetfile):
    """
    Ensure that arithmetic operations on GONetFile instances are not clipped
    to the original 16-bit [0, 65535] range, and can exceed those bounds.
    """
    # Multiply all values by 2 — values should now exceed 65535
    result = fake_gonetfile * 700

    assert result.red.max() > 65535, "Red channel is unexpectedly clipped"
    assert result.green.max() > 65535, "Green channel is unexpectedly clipped"
    assert result.blue.max() > 65535, "Blue channel is unexpectedly clipped"

    # Subtract to push values negative
    result_neg = fake_gonetfile - 1000
    assert result_neg.red.min() < 0, "Red channel did not go negative as expected"
    assert result_neg.green.min() < 0, "Green channel did not go negative as expected"
    assert result_neg.blue.min() < 0, "Blue channel did not go negative as expected"

def test_gonetfile_getitem(fake_gonetfile):
    go = fake_gonetfile

    # Apply slicing
    cropped = go[:, 1:3]

    # --- Assertions ---

    # Check that the output is a GONetFile
    assert isinstance(cropped, GONetFile)

    # Check shape changes
    assert cropped.red.shape == (4, 2)
    assert cropped.green.shape == (4, 2)
    assert cropped.blue.shape == (4, 2)

    # Check that the values are correct
    np.testing.assert_array_equal(cropped.red, np.ones((4, 2)) * 100)
    np.testing.assert_array_equal(cropped.green, np.ones((4, 2)) * 200)
    np.testing.assert_array_equal(cropped.blue, np.ones((4, 2)) * 300)

    # Check that filename and meta are preserved
    assert cropped.filename == 'fake'
    assert cropped._meta == {"dummy": True}
    assert cropped._filetype == go._filetype