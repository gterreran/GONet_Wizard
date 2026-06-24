# Windows desktop installer

This folder contains the local Windows installer tooling for GONet Wizard.

The Windows installer is intentionally GUI-first. It installs the frozen
`GONet Wizard.exe` desktop application and creates Start Menu shortcuts. It does
not add `GONet_Wizard` or `gonet-wizard` command-line entry points to `PATH`.
Users who want the CLI should install the Python package with `pip` or `pipx`.

## Prerequisites

Build and test on Windows. PyInstaller does not cross-compile Windows apps from
macOS or Linux.

Recommended local environment:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,build]"
pytest
```

Install Inno Setup 6 and make sure `ISCC.exe` is available either on `PATH` or
in one of the standard install locations:

- `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
- `C:\Program Files\Inno Setup 6\ISCC.exe`

If it is installed elsewhere, pass `-InnoSetupCompiler` to the build script.

## Build the frozen app

From the repository root:

```powershell
python -m PyInstaller build_tools\pyinstaller\gonet_wizard_gui.spec --clean --noconfirm
```

Then smoke test the raw frozen app before building an installer:

```powershell
.\dist\"GONet Wizard"\"GONet Wizard.exe"
```

Check the launcher, `show`, `extract`, and `dashboard`.

## Build the installer

To force a fresh PyInstaller build and then create the installer:

```powershell
powershell -ExecutionPolicy Bypass -File build_tools\windows\build_installer.ps1 -ForcePyInstaller
```

To reuse an existing `dist\GONet Wizard\` folder:

```powershell
powershell -ExecutionPolicy Bypass -File build_tools\windows\build_installer.ps1 -SkipPyInstaller
```

The default output is:

```text
dist\GONet-Wizard-<version>-Windows-x64-unsigned-Setup.exe
dist\SHA256SUMS-Windows.txt
```

Use an explicit test version with:

```powershell
powershell -ExecutionPolicy Bypass -File build_tools\windows\build_installer.ps1 -Version 0.0.0-windows-test -ForcePyInstaller
```

## Installer behavior

The first installer path is intentionally simple:

- installs per-user under `%LOCALAPPDATA%\Programs\GONet Wizard`;
- creates a Start Menu shortcut;
- offers an optional Desktop shortcut;
- supports normal Windows uninstall;
- does not require administrator privileges;
- does not modify the user's `PATH`.

## Local smoke test

After building `Setup.exe`, test like a user would:

1. Run the installer.
2. Launch GONet Wizard from the Start Menu.
3. Launch it from the Desktop shortcut if selected.
4. Check the launcher, `show`, `extract`, and `dashboard`.
5. Close and reopen the app.
6. Uninstall from Windows Settings.
7. Reinstall and repeat a basic launch test.

## WebView2 note

The Windows GUI uses PyWebView. On modern Windows machines, the Microsoft Edge
WebView2 Runtime is usually already present. If users report that the desktop
window cannot open, check whether WebView2 is installed before changing the
PyInstaller configuration.
