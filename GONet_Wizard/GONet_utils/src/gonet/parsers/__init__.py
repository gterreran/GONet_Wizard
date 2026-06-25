"""
Unified interface for GONet file parsers.

The :mod:`.gonet.parsers` package provides low-level parsing utilities for reading
GONet data and metadata from various file formats. It serves as the centralized
entry point for extracting raw image arrays and structured metadata from both
processed and unprocessed GONet camera files.

**Modules**

- :mod:`.tiff_reader` — Parser for standard TIFF image files.
- :mod:`.raw_reader` — Parser for uncompressed RAW `.jpg` files produced by GONet cameras.
- :mod:`.exif_reader` — Parser for extracting and structuring EXIF metadata from JPEG headers.

"""

from GONet_Wizard.GONet_utils.src.gonet.parsers.tiff_reader import parse_tiff_file
from GONet_Wizard.GONet_utils.src.gonet.parsers.raw_reader import parse_raw_file
from GONet_Wizard.GONet_utils.src.gonet.parsers.exif_reader import parse_exif_metadata