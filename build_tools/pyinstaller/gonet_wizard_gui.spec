# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the double-clickable GONet Wizard desktop GUI.

Build from the repository root with:

    pyinstaller build_tools/pyinstaller/gonet_wizard_gui.spec --clean --noconfirm

This spec intentionally builds an ``onedir`` app rather than a ``onefile`` app.
That keeps startup faster and makes macOS signing/notarization easier later.
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


APP_NAME = "GONet Wizard"
BUNDLE_IDENTIFIER = "org.adlerplanetarium.gonetwizard"

# Keep GONet data under GONet_Wizard/... inside the frozen bundle. The runtime
# helpers in GONet_Wizard.resources know how to locate this layout.
datas = collect_gonet_datas() + collect_dash_component_datas()

# Dash/Flask callbacks, pywebview backends, and command modules include a few
# dynamically discovered imports. Collect them with a runtime filter so testing,
# notebook, and documentation helpers do not inflate the frozen app.
hiddenimports = collect_runtime_hiddenimports()

icon = PACKAGE_ROOT / "static" / "img" / "logo" / "GONet_Wizard.ico"
if sys.platform == "darwin":
    icon = PACKAGE_ROOT / "static" / "img" / "logo" / "GONet_Wizard.icns"


a = Analysis(
    [str(PACKAGE_ROOT / "desktop.py")],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon),
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

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=str(icon),
        bundle_identifier=BUNDLE_IDENTIFIER,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": BUNDLE_IDENTIFIER,
            "NSHighResolutionCapable": "True",
        },
    )
