import numpy as np
import pytest
from GONet_Wizard.GONet_utils import GONetFile
import tifffile
from PIL import Image
from astropy.io import fits

@pytest.fixture
def dolus_gonetfile(tmp_path) -> GONetFile:
    """
    Fixture that loads the verified Dolus file using GONetFile.from_file.
    Only used after the method is independently tested.
    """
    source_file = "tests/Dolus_250307_155311_1741362791.jpg"
    test_file = tmp_path / "Dolus.jpg"
    with open(source_file, 'rb') as src, open(test_file, 'wb') as dst:
        dst.write(src.read())
    return GONetFile.from_file(str(test_file), meta=True)


def test_write_to_tiff(tmp_path, dolus_gonetfile):
    """
    Test that write_to_tiff correctly writes a TIFF file
    with the expected shape, dtype, and content from the GONetFile.

    This test disables white balance to ensure a direct pixel comparison.
    """
    output_file = tmp_path / "dolus_split.tiff"

    # Write TIFF with white_balance=False to match expected values
    dolus_gonetfile.write_to_tiff(str(output_file), white_balance=False)

    # Ensure the file was written
    assert output_file.exists(), "TIFF file was not created."

    # Load the written TIFF
    with tifffile.TiffFile(output_file) as tif:
        image = tif.asarray()
        assert image.shape[0] == 3, "Expected 3-channel RGB TIFF"
        assert image.dtype == np.uint16, "TIFF data should be uint16"

    # Rebuild the expected RGB stack
    expected_stack = np.stack([
        np.clip(dolus_gonetfile.red, 0, 65535).astype(np.uint16),
        np.clip(dolus_gonetfile.green, 0, 65535).astype(np.uint16),
        np.clip(dolus_gonetfile.blue, 0, 65535).astype(np.uint16),
    ], axis=0)

    # Compare pixel values exactly
    np.testing.assert_array_equal(image, expected_stack)


def test_write_to_jpeg(tmp_path, dolus_gonetfile):
    """
    Test that write_to_jpeg produces a valid 8-bit RGB JPEG image
    with content that matches the rescaled GONetFile data.
    """
    jpeg_path = tmp_path / "dolus_output.jpg"

    # Write JPEG
    dolus_gonetfile.write_to_jpeg(str(jpeg_path))

    # Check the file exists
    assert jpeg_path.exists(), "JPEG file was not created."

    # Open the written JPEG
    with Image.open(jpeg_path) as img:
        assert img.mode == "RGB", "JPEG should be RGB"
        img_array = np.array(img)

    # Check dimensions match
    h, w = dolus_gonetfile.red.shape
    assert img_array.shape == (h, w, 3), f"Unexpected image shape: {img_array.shape}"

    # Recompute the expected uint8 RGB
    def to_uint8(arr):
        arr = np.clip(arr, 0, 2**16 - 1)
        return np.round(arr / (2**16 - 1) * 255).astype(np.uint8)

    r_gain, b_gain = dolus_gonetfile.meta["JPEG"]["WB"]
    expected_rgb = np.stack([
        to_uint8(dolus_gonetfile.red * r_gain),
        to_uint8(dolus_gonetfile.green),
        to_uint8(dolus_gonetfile.blue * b_gain)
    ], axis=-1)

    # JPEG is lossy, so allow a small tolerance (e.g., ±1)
    diff = np.abs(img_array.astype(np.int16) - expected_rgb.astype(np.int16))
    # Allow up to 5 units of deviation
    assert np.max(diff) <= 5, f"Max deviation {np.max(diff)} exceeds allowed tolerance."


def test_write_to_fits(dolus_gonetfile, tmp_path):
    """
    Test that write_to_fits correctly saves RGB image data and metadata
    into a valid multi-extension FITS file using the Dolus GONet file.
    """
    # Write to a temporary FITS file
    fits_path = tmp_path / "output.fits"
    dolus_gonetfile.write_to_fits(str(fits_path))

    # Confirm the FITS file was created
    assert fits_path.exists(), "FITS file was not created."

    # Open and inspect the FITS file
    with fits.open(fits_path) as hdul:
        assert len(hdul) == 4, "FITS should have 1 primary + 3 image HDUs."

        red_hdu, green_hdu, blue_hdu = hdul[1], hdul[2], hdul[3]

        # Check channel and extension names
        for hdu, name in zip([red_hdu, green_hdu, blue_hdu], ['RED', 'GREEN', 'BLUE']):
            assert hdu.header.get("EXTNAME") == name
            assert hdu.header.get("CHANNEL") == name

        # Check select metadata entries
        red_header = red_hdu.header
        assert red_header.get("GONETCAM") == "GONetDolus"
        assert "EXPTIME" in red_header
        assert "IMGWIDTH" in red_header

        # Compare data arrays
        np.testing.assert_array_almost_equal(red_hdu.data, dolus_gonetfile.red)
        np.testing.assert_array_almost_equal(green_hdu.data, dolus_gonetfile.green)
        np.testing.assert_array_almost_equal(blue_hdu.data, dolus_gonetfile.blue)


