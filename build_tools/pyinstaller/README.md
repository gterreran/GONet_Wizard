# PyInstaller build scaffolding

This folder contains the first raw frozen-build scaffolding for GONet Wizard.
It is intentionally **not** an installer yet.  The goal is to prove that the app
can be frozen while still finding bundled templates, static files, icons, and
small package data files.

Run all commands from the repository root.

## Install build dependencies

```bash
pip install -e ".[build]"
```

## GUI build

```bash
pyinstaller build_tools/pyinstaller/gonet_wizard_gui.spec --clean --noconfirm
```

Expected outputs:

- macOS: `dist/GONet Wizard.app`
- Windows/Linux raw build: `dist/GONet Wizard/`

The GUI spec is windowed/console-free because this is the executable that will
later become the double-clickable desktop app.


## Unsigned macOS DMG

Once the raw macOS `.app` passes the smoke checks, create a test DMG with:

```bash
build_tools/macos/build_dmg.sh
```

Expected output:

```text
dist/GONet-Wizard-macOS-<arch>-unsigned.dmg
```

The DMG is intentionally unsigned and not notarized at this stage. It is suitable
for local testing and GitHub release candidates, but macOS Gatekeeper may block
first launch on another machine. See `build_tools/macos/README.md` for the
internal-testing install flow.

## CLI build

```bash
pyinstaller build_tools/pyinstaller/gonet_wizard_cli.spec --clean --noconfirm
```

Expected output:

- `dist/gonet-wizard/`

The CLI build keeps a console window and is mainly useful as a diagnostic/power
user executable.


## Size-cleanup notes

The specs intentionally keep Dash component package data broad because Dash reads
metadata and serves JavaScript/CSS sidecar files at runtime.  Python hidden
imports are filtered separately in `_runtime_selection.py` so development,
testing, notebook, and documentation modules do not inflate the frozen app.

If a future build fails with a missing runtime module, prefer adding a narrow
package or module to `RUNTIME_HIDDENIMPORT_PACKAGES` rather than reverting to
unfiltered `collect_submodules(...)` calls.

For the cleanest release-sized build, build from a fresh environment containing
only the runtime dependencies plus the `build` extra, not the full `dev` or
`docs` extras.  Keep using the dev environment for tests.

## First smoke checks

After building, test the following before making installer work:

```bash
# from the frozen CLI folder
./gonet-wizard --version
./gonet-wizard --help

# from the frozen GUI app/folder
# launch GONet Wizard and confirm the launcher page, forms, CSS, JS, and icons load
```

Also check workflows that touch bundled resources:

- launcher opens with the normal stylesheet and logo;
- `show` form opens and renders a preview window;
- `extract` form opens and the extraction Dash app loads its assets;
- `dashboard` launches and its Dash assets load;
- no `file_system_backend/`, logs, cache, or runtime temp directories appear in
  the installed/frozen app directory.

## Notes

The build specs keep package data under `GONet_Wizard/...` in the frozen bundle.
The runtime helper `GONet_Wizard.resources` is responsible for finding those
resources in source checkouts, installed wheels, and frozen apps.
