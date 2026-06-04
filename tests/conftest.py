from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pytest

from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_utils.src.gonet.filetypes import FileType
from GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw import GONetFileRaw


TESTS_DIR = Path(__file__).resolve().parent
DOLUS_JPG = TESTS_DIR / "Dolus_250307_155311_1741362791.jpg"
DOLUS_TIFF = TESTS_DIR / "Dolus_250307_155311_1741362791.tiff"
DOLUS_META = TESTS_DIR / "Dolus_expected_meta.json"


@pytest.fixture
def small_gonet_file() -> GONetFile:
    return GONetFile(
        filename="small.jpg",
        blue=np.arange(9, dtype=float).reshape(3, 3),
        green=np.arange(10, 19, dtype=float).reshape(3, 3),
        red=np.arange(20, 29, dtype=float).reshape(3, 3),
        meta={"exposure_time": 5.0},
        filetype=FileType.SCIENCE,
    )


@pytest.fixture
def small_raw_file() -> GONetFileRaw:
    base = np.arange(6, dtype=float).reshape(2, 3)
    return GONetFileRaw(
        filename="raw.jpg",
        blue=base + 100,
        green1=base + 200,
        green2=base + 300,
        red=base + 400,
        meta={"camera": "test"},
        filetype=FileType.SCIENCE,
        is_bayer_planes=False,
    )
