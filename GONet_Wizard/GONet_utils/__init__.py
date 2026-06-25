"""
This subpackage provides utilities for handling and processing data
collected by GONet cameras.

The subpackage exposes the classes :class:`.GONetFile` and :class:`.GONetFileRaw` for reading and parsing GONet raw data files.
It also provides the constant :data:`.DATA_SPEC`, which defines the data specification for GONet files.
"""

from GONet_Wizard.GONet_utils.src.gonet.gonet_file import GONetFile # noqa: F401
from GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw import GONetFileRaw # noqa: F401
from GONet_Wizard.GONet_utils.src.data_spec import DATA_SPEC # noqa: F401