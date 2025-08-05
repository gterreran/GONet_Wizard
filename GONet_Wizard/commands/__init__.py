"""
GONet Wizard CLI Command Interface.

This module provides high-level entry points for various command-line tools
used in the GONet Wizard suite. These tools are primarily intended for manual
or scripted interaction with GONet devices and their associated data products.

**Included Commands**

- :mod:`.run_dashboard` : Launch the interactive GONet dashboard server.
- :mod:`.show` : Visualize GONet image data interactively or save as PDF.
- :mod:`.show_meta` : Display metadata from one or more GONet files.
- :mod:`.snap` : Trigger a remote image acquisition and retrieve new files.
- :mod:`.terminate` : Stop all remote imaging processes and clean up.
- :mod:`.extract` : Extract counts from a region of a GONet image.
- :mod:`.connect` : SSH Connection Utilities for GONet Remote Access.

"""

from GONet_Wizard.commands.run_dashboard import run
from GONet_Wizard.commands.show import show_gonet_files
from GONet_Wizard.commands.show_meta import show_metadata
from GONet_Wizard.commands.snap import take_snapshot
from GONet_Wizard.commands.terminate import terminate_imaging
from GONet_Wizard.commands.extract import extract_counts_from_GONet 
