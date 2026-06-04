import importlib
import sys
import types

import pytest


def test_main_delegates_to_cli(monkeypatch):
    from GONet_Wizard import __main__

    called = {}

    def fake_main(argv=None):
        called["argv"] = argv

    monkeypatch.setattr(__main__._cli, "main", fake_main)

    __main__.main(["show", "image.tiff"])

    assert called == {"argv": ["show", "image.tiff"]}


def test_branding_resource_path_uses_pyinstaller_meipass(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")
    monkeypatch.setattr(branding.sys, "_MEIPASS", "/tmp/gonet-bundle", raising=False)

    assert branding._resource_path("static", "icon.ico") == "/tmp/gonet-bundle/static/icon.ico"


def test_branding_default_icon_path_depends_on_platform(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")

    monkeypatch.setattr(branding.platform, "system", lambda: "Darwin")
    assert branding._default_icon_path().endswith("static/img/logo/GONet_Wizard.icns")

    monkeypatch.setattr(branding.platform, "system", lambda: "Linux")
    assert branding._default_icon_path().endswith("static/img/logo/GONet_Wizard.ico")


def test_set_dock_icon_once_is_noop_if_already_set(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")
    monkeypatch.setattr(branding, "_ICON_SET", True)
    monkeypatch.setattr(branding.platform, "system", lambda: "Darwin")

    # This would be imported only if the early return failed.
    sys.modules.pop("AppKit", None)
    branding.set_dock_icon_once("missing.icns")

    assert branding._ICON_SET is True


def test_set_dock_icon_once_is_noop_on_non_macos(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")
    monkeypatch.setattr(branding, "_ICON_SET", False)
    monkeypatch.setattr(branding.platform, "system", lambda: "Linux")

    branding.set_dock_icon_once("missing.ico")

    assert branding._ICON_SET is False


def test_set_dock_icon_once_uses_appkit_on_macos(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")
    monkeypatch.setattr(branding, "_ICON_SET", False)
    monkeypatch.setattr(branding.platform, "system", lambda: "Darwin")

    calls = {}

    class FakeImageInstance:
        pass

    class FakeNSImage:
        @classmethod
        def alloc(cls):
            return cls()

        def initWithContentsOfFile_(self, path):
            calls["path"] = path
            return FakeImageInstance()

    class FakeApplication:
        def setApplicationIconImage_(self, image):
            calls["image"] = image

    class FakeNSApplication:
        @staticmethod
        def sharedApplication():
            return FakeApplication()

    fake_appkit = types.SimpleNamespace(
        NSApplication=FakeNSApplication,
        NSImage=FakeNSImage,
    )
    monkeypatch.setitem(sys.modules, "AppKit", fake_appkit)

    branding.set_dock_icon_once("icon.icns")

    assert calls["path"] == "icon.icns"
    assert isinstance(calls["image"], FakeImageInstance)
    assert branding._ICON_SET is True


def test_patch_webview_start_is_idempotent(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")

    def already_patched():
        return None

    already_patched._gonet_patched = True
    monkeypatch.setattr(branding.webview, "start", already_patched)

    branding.patch_webview_start()

    assert branding.webview.start is already_patched


def test_patch_webview_start_wraps_callback_and_forces_cocoa_on_macos(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")
    monkeypatch.setattr(branding.platform, "system", lambda: "Darwin")

    calls = {}

    def fake_start(callback, *args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        callback()
        return "started"

    def fake_set_dock_icon_once():
        calls["icon"] = True

    def user_callback():
        calls["user"] = True

    monkeypatch.setattr(branding.webview, "start", fake_start)
    monkeypatch.setattr(branding, "set_dock_icon_once", fake_set_dock_icon_once)

    branding.patch_webview_start()
    result = branding.webview.start(user_callback, "window")

    assert result == "started"
    assert calls["args"] == ("window",)
    assert calls["kwargs"] == {"gui": "cocoa"}
    assert calls["icon"] is True
    assert calls["user"] is True


def test_patch_webview_start_respects_on_ready_kwarg_and_existing_gui(monkeypatch):
    branding = pytest.importorskip("GONet_Wizard._branding")
    monkeypatch.setattr(branding.platform, "system", lambda: "Darwin")

    calls = {}

    def fake_start(callback, *args, **kwargs):
        calls["kwargs"] = kwargs
        callback()
        return "started"

    def fake_set_dock_icon_once():
        calls["icon"] = True

    def user_callback():
        calls["user"] = True

    monkeypatch.setattr(branding.webview, "start", fake_start)
    monkeypatch.setattr(branding, "set_dock_icon_once", fake_set_dock_icon_once)

    branding.patch_webview_start()
    result = branding.webview.start(on_ready=user_callback, gui="qt")

    assert result == "started"
    assert calls["kwargs"] == {"gui": "qt"}
    assert calls["icon"] is True
    assert calls["user"] is True
