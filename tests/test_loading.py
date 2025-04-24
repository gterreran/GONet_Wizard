import json
import numpy as np
import pytest
from GONet_Wizard.GONet_utils import GONetFile
from pathlib import Path
from GONet_Wizard.GONet_utils.src.gonetfile import scale_uint12_to_16bit_range

def verify_proper_load(source_file: str, tmp_path: str, pattern_red: np.ndarray, pattern_green: np.ndarray, pattern_blue: np.ndarray):
    """
    Verify that the red, green, and blue channels in a GONetFile instance
    match the expected Dolus pattern.

    This test uses a controlled test file ("Dolus") and compares the parsed
    image channels against a known pattern. Metadata is compared against a
    reference JSON file containing expected EXIF values.
    """

    # Load expected EXIF metadata from JSON file
    with open("tests/Dolus_expected_meta.json", "r") as f:
        expected_metadata = json.load(f)

    # Copy the Dolus file into a temp directory for isolated testing
    extension = source_file.split('.')[-1]
    test_file = str(tmp_path / f"Dolus.{extension}")
    with open(source_file, 'rb') as src, open(test_file, 'wb') as dst:
        dst.write(src.read())

    # Parse the file using the full class pipeline with metadata extraction
    gonet = GONetFile.from_file(test_file, meta=True)

    assert gonet.filename == test_file

    # Confirm that each channel was parsed and scaled correctly
    np.testing.assert_array_equal(gonet.red, pattern_red)
    np.testing.assert_array_equal(gonet.green, pattern_green)
    np.testing.assert_array_equal(gonet.blue, pattern_blue)

    # Confirm that metadata matches the known expected fields
    meta = gonet.meta

    # Allow meta to be None, and only perform checks if it's a dict
    assert meta is None or isinstance(meta, dict), "Metadata must be a dictionary or None."

    if meta is not None:
        for key, expected in expected_metadata.items():
            assert key in meta, f"Missing expected metadata key: {key}"
            actual = meta[key]

            if isinstance(expected, float):
                assert abs(actual - expected) < 1e-6, f"Metadata mismatch for key '{key}'"
            else:
                assert actual == expected, f"Metadata mismatch for key '{key}'"


def test_loading_from_raw_file(tmp_path):
    """
    Test that GONetFile.from_file correctly parses a GONet .jpg raw file and
    extracts both RGB image data and metadata.

    """

    source_file = "tests/Dolus_250307_155311_1741362791.jpg"

    # Generate the expected RGB arrays using the known pattern logic
    array = np.array([
        range(i, i + int(GONetFile.PIXEL_PER_LINE / 2))
        for i in range(0, int(GONetFile.PIXEL_PER_COLUMN / 2))
    ])
    red = scale_uint12_to_16bit_range(np.clip(array, 0, 4095))
    green = scale_uint12_to_16bit_range(np.clip(array * 5, 0, 4095))
    blue = scale_uint12_to_16bit_range(np.clip(array * 2, 0, 4095))

    verify_proper_load(source_file, tmp_path, red, green, blue)


def test_loading_from_tiff_file(tmp_path):
    """
    Test that GONetFile.from_file correctly parses a GONet .tiff file and
    extracts both RGB image data and metadata.

    """

    source_file = "tests/Dolus_250307_155311_1741362791.tiff"

    # Generate the expected RGB arrays using the known pattern logic
    array = np.array([
        np.arange(i,(i+int(GONetFile.PIXEL_PER_LINE/2)))
        for i in np.arange(0,int(GONetFile.PIXEL_PER_COLUMN/2))
    ])

    def approx_Domus(arr):
        return arr*16 + np.floor(arr*np.float32(((2**16-1)/(2**12-1)-16)))

    red = np.clip(approx_Domus(array), 0, 2**16-1)
    green = np.clip(approx_Domus(array*5), 0, 2**16-1)
    blue = np.clip(approx_Domus(array*2), 0, 2**16-1)

    verify_proper_load(source_file, tmp_path, red, green, blue)

    


# @pytest.fixture
# def dolus_gonetfile(tmp_path) -> GONetFile:
#     """
#     Fixture that loads the verified Dolus file using GONetFile.from_file.
#     Only used after the method is independently tested.
#     """
#     source_file = "tests/Dolus_250307_155311_1741362791.jpg"
#     test_file = tmp_path / "Dolus.jpg"
#     with open(source_file, 'rb') as src, open(test_file, 'wb') as dst:
#         dst.write(src.read())
#     return GONetFile.from_file(str(test_file), meta=True)


def is_safe_scalar(val):
    return isinstance(val, (int, float, str, bool, type(None)))

def assert_safe_meta(meta, path="meta"):
    """
    Recursively assert that all metadata values are safe scalars.
    """
    if isinstance(meta, dict):
        for key, val in meta.items():
            new_path = f"{path}.{key}"
            assert_safe_meta(val, new_path)
    elif isinstance(meta, (list, tuple)):
        for i, val in enumerate(meta):
            new_path = f"{path}[{i}]"
            assert_safe_meta(val, new_path)
    else:
        assert is_safe_scalar(meta), f"{path} has unsafe type {type(meta).__name__}: {meta}"

def test_metadata_is_safe_or_none(tmp_path):
    filename = f"Dolus_250307_155311_1741362791.jpg"
    source = Path("tests") / filename
    target = tmp_path / f"Dolus.jpg"
    target.write_bytes(source.read_bytes())

    gnf = GONetFile.from_file(str(target))
    
    
    assert_safe_meta(gnf.meta)