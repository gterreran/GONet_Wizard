"""
Unified interface for image export utilities in GONet.

The :mod:`gonet.writers` package consolidates output functions that convert
GONet image data into standard file formats for external use and analysis.
Each writer handles both :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`
and :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw`
instances, automatically managing color channel handling, scaling, and metadata propagation.

**Modules**

- :mod:`.jpeg` — Export GONet data to 8-bit JPEG format.
- :mod:`.tiff` — Export GONet data to 16-bit TIFF format.
- :mod:`.fits` — Export GONet data to multi-extension FITS format.

"""

from GONet_Wizard.GONet_utils.src.gonet.writers.jpeg import write_to_jpeg
from GONet_Wizard.GONet_utils.src.gonet.writers.tiff import write_to_tiff
from GONet_Wizard.GONet_utils.src.gonet.writers.fits import write_to_fits