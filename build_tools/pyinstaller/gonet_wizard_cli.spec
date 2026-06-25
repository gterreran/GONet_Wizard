# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for a console-capable GONet Wizard CLI executable.

Build from the repository root with:

    pyinstaller build_tools/pyinstaller/gonet_wizard_cli.spec --clean --noconfirm

This is optional for end users, but useful as a frozen diagnostic executable and
for power users who want CLI functionality without a Python environment.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path.cwd()
PACKAGE_ROOT = ROOT / "GONet_Wizard"
PYINSTALLER_ROOT = ROOT / "build_tools" / "pyinstaller"
sys.path.insert(0, str(PYINSTALLER_ROOT))

from _runtime_selection import (  # noqa: E402
    EXCLUDES,
    collect_dash_component_datas,
    collect_gonet_datas,
    collect_runtime_hiddenimports,
)


APP_NAME = "gonet-wizard"

datas = collect_gonet_datas() + collect_dash_component_datas()
hiddenimports = collect_runtime_hiddenimports()


a = Analysis(
    [str(PACKAGE_ROOT / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(PYINSTALLER_ROOT / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
