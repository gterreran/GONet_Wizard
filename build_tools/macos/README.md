# macOS DMG build helper

This folder contains the first unsigned macOS DMG wrapper for the PyInstaller
GUI app. It is intended for local testing and GitHub release candidates, not for
App Store distribution.

Run from the repository root after the GUI `.app` build is working:

```bash
build_tools/macos/build_dmg.sh
```

The script will reuse `dist/GONet Wizard.app` if it already exists. If the app is
missing, it will build it with:

```bash
python -m PyInstaller build_tools/pyinstaller/gonet_wizard_gui.spec --clean --noconfirm
```

Expected output:

```text
dist/GONet-Wizard-<version>-macOS-<arch>-unsigned.dmg
```

Useful options:

```bash
# Require an existing .app and only create the DMG
build_tools/macos/build_dmg.sh --skip-pyinstaller

# Force a fresh PyInstaller app build before making the DMG
build_tools/macos/build_dmg.sh --force-pyinstaller

# Choose a custom output name
build_tools/macos/build_dmg.sh --dmg-name GONet-Wizard-test.dmg

# Override the version label used in the default filename and README
build_tools/macos/build_dmg.sh --version 0.3.0-test
```

The DMG contains:

- `GONet Wizard.app`
- an `Applications` shortcut
- `README-FIRST.txt` with unsigned-build launch notes

Because this first DMG is unsigned and not notarized, macOS Gatekeeper may block
first launch on another machine. For internal testing, right-click/control-click
the app and choose **Open**, or use **System Settings > Privacy & Security** to
allow the app after the first blocked launch.

For GitHub-based distribution, keep generated DMGs out of the repository and upload them as GitHub Release assets. The `Build macOS DMG` GitHub Actions workflow can build a short-lived test artifact manually, or attach the DMG to a draft release when a `v*` tag is pushed.
