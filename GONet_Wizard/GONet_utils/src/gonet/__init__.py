"""
Core GONet data structures, parsers, and utilities.

The :mod:`.gonet` package provides the foundational classes and helper
functions used throughout the GONet data processing ecosystem. It defines
the object model for handling calibrated and raw camera data, along with
tools for reading, writing, and analyzing GONet image files.

This package forms the backbone of the GONet data model. It unifies
low-level binary parsing, high-level metadata management, and export
routines into a single, object-oriented framework designed for robustness,
extensibility, and scientific reproducibility.

**Submodules**
--------------
- :mod:`.gonet_file` — Core :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile` class for processed GONet images.
- :mod:`.gonet_file_raw` — Specialized :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw` class for raw Bayer data.
- :mod:`.filetypes` — Enumeration of GONet file types (e.g., SCIENCE, FLAT, DARK).
- :mod:`.config` — Constants describing the GONet camera sensor geometry.
- :mod:`.io_utils` — Low-level I/O utilities for scaling and range conversions.
- :mod:`.parsers` — File readers for TIFF, RAW `.jpg`, and EXIF metadata.
- :mod:`.writers` — Output utilities for exporting GONet data to TIFF, JPEG, and FITS.
- :mod:`.analysis_utils` — Image preprocessing and calibration tools.

"""