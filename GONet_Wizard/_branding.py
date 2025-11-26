"""
Branding module for GONet Wizard pywebview windows.
===================================================

Purpose
-------
Provides centralized, process-wide branding for all pywebview windows launched
by the GONet Wizard package. On macOS, this module sets the Dock icon to a
custom `.icns` file so that *every* window shares the same branded appearance.
It achieves this by patching pywebview's `start()` function to ensure the Dock
icon is applied automatically after Cocoa initialization.

When to use
-----------
Call :func:`patch_webview_start` once, early in your application entry point
(e.g., in ``__main__.py``). After that, every call to ``webview.start()`` across
the entire package will:

- Use the Cocoa backend on macOS by default (if none specified).
- Invoke :func:`set_dock_icon_once` after the Cocoa app is initialized,
  ensuring the Dock icon displays correctly.

Notes
-----
- This mechanism is primarily useful during development or when running the app
  unbundled. When the project is packaged as a proper macOS ``.app`` bundle
  (via PyInstaller or py2app) and the bundle Info.plist specifies an embedded
  ``.icns`` icon, macOS will use that automatically, rendering this module
  unnecessary.
- Icon paths are hardcoded by design. If the icons are moved or renamed, this
  module will fail immediately, prompting you to update it.

"""

from __future__ import annotations

import sys, platform, webview
from pathlib import Path

_ICON_SET = False  # process-wide guard


def _resource_path(*rel_parts: str) -> str:
    """
    Build an absolute path to a resource shipped with the package.

    Parameters
    ----------
    rel_parts : :class:`str`
        One or more path segments relative to this file's directory (or the
        PyInstaller `_MEIPASS` temp directory if present).

    Returns
    -------
    :class:`str`
        Absolute filesystem path to the requested resource.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base.joinpath(*rel_parts))


def _default_icon_path() -> str:
    """
    Return the hardcoded path to the platform-appropriate icon.

    On macOS this is the `.icns` used for the Dock icon. On Windows you may
    choose to point to a `.ico` if you later add Windows-specific handling.

    Parameters
    ----------
    None

    Returns
    -------
    :class:`str`
        Absolute filesystem path to the icon file.
    """
    if platform.system() == "Darwin":
        return _resource_path("static", "img", "logo", "GONet_Wizard.icns")
    else:
        return _resource_path("static", "img", "logo", "GONet_Wizard.ico")


def set_dock_icon_once(path: str | None = None) -> None:
    """
    Set the macOS Dock icon for this process exactly once.

    This function is a no-op on non-macOS platforms. On macOS it calls the
    native Cocoa API via PyObjC to set the application icon.

    Parameters
    ----------
    path : :class:`str`, optional
        Absolute path to a `.icns` file. If omitted, uses `_default_icon_path()`.

    Returns
    -------
    None

    Raises
    ------
    ImportError
        If PyObjC is not installed on macOS.
    Exception
        Any error raised by Cocoa if the icon cannot be loaded or applied.
    """
    global _ICON_SET
    if _ICON_SET:
        return
    if platform.system() != "Darwin":
        return

    icns = path or _default_icon_path()

    from AppKit import NSApplication, NSImage  # type: ignore

    img = NSImage.alloc().initWithContentsOfFile_(icns)
    NSApplication.sharedApplication().setApplicationIconImage_(img)
    _ICON_SET = True


def patch_webview_start() -> None:
    """
    Patch :func:`webview.start` to apply GONet Wizard branding automatically.

    Scope
    -----
    This function replaces the original ``webview.start`` with a wrapper that:
    
    1. Forces the Cocoa backend on macOS if no backend is explicitly provided.
    2. Injects a startup callback that sets the Dock icon once Cocoa is
       initialized.
    3. Preserves any user-supplied startup callback, calling it after the icon
       is applied.
    4. Has no effect (no-op) if the patch has already been applied.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Raises
    ------
    ImportError
        If ``pywebview`` is not installed or cannot be imported.
    """

    if getattr(webview.start, "_gonet_patched", False):
        return

    _orig_start = webview.start

    def _wrapped(*args, **kwargs):
        # Extract any user-supplied startup callback
        user_cb = None
        rest_args = args
        if args and callable(args[0]):
            user_cb = args[0]
            rest_args = args[1:]
        elif "on_ready" in kwargs and callable(kwargs["on_ready"]):
            user_cb = kwargs.pop("on_ready")

        def _on_ready():
            from GONet_Wizard._branding import set_dock_icon_once
            set_dock_icon_once()
            if user_cb:
                user_cb()

        if platform.system() == "Darwin" and "gui" not in kwargs:
            kwargs["gui"] = "cocoa"

        return _orig_start(_on_ready, *rest_args, **kwargs)

    _wrapped._gonet_patched = True
    webview.start = _wrapped
