"""
GONet Wizard CLI Command Interface.

This module provides high-level entry points for various command-line tools
used in the GONet Wizard suite. These tools are primarily intended for manual
or scripted interaction with GONet devices and their associated data products.

**Included Commands**

- :func:`.run_dashboard` : Launch the interactive GONet dashboard server.
- :func:`.show` : Visualize GONet image data interactively or save as PDF.
- :func:`.show_meta` : Display metadata from one or more GONet files.
- :func:`.snap` : Trigger a remote image acquisition and retrieve new files.
- :func:`.terminate_imaging` : Stop all remote imaging processes and clean up.

"""

from GONet_Wizard.commands.run_dashboard import run
from GONet_Wizard.commands.show import show_gonet_files
from GONet_Wizard.commands.show_meta import show_metadata
from GONet_Wizard.commands.snap import take_snapshot

from GONet_Wizard.commands.terminate import terminate_imaging
