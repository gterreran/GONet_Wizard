"""PyInstaller hook for GONet Wizard package data and runtime submodules."""

from __future__ import annotations

import sys
from pathlib import Path


# Import the shared collection rules from the parent pyinstaller folder. PyInstaller
# executes hooks in its own context, so make the sibling helper explicit.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _runtime_selection import (  # noqa: E402
    EXCLUDES,
    collect_dash_component_datas,
    collect_gonet_datas,
    collect_runtime_hiddenimports,
)


datas = collect_gonet_datas() + collect_dash_component_datas()
hiddenimports = collect_runtime_hiddenimports(["GONet_Wizard"])
excludedimports = EXCLUDES
