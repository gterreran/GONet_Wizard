from pathlib import Path


def test_desktop_entrypoint_delegates_to_gui_command(monkeypatch):
    import types
    import sys

    from GONet_Wizard import desktop

    called = {}

    def fake_cli_main(argv=None):
        called["argv"] = argv

    fake_cli = types.SimpleNamespace(main=fake_cli_main)
    monkeypatch.setitem(sys.modules, "GONet_Wizard.cli", fake_cli)

    desktop.main(["--port", "5051"])

    assert called == {"argv": ["gui", "--port", "5051"]}


def test_resource_helpers_find_static_and_templates():
    from GONet_Wizard.resources import resource_path, static_dir, template_dir

    assert resource_path().is_dir()
    assert static_dir("css", "style.css", must_exist=True).is_file()
    assert template_dir("index.html", must_exist=True).is_file()


def test_resource_path_supports_pyinstaller_package_layout(monkeypatch, tmp_path: Path):
    from GONet_Wizard import resources

    bundled = tmp_path / "_MEIPASS" / "GONet_Wizard" / "static" / "css"
    bundled.mkdir(parents=True)
    css = bundled / "style.css"
    css.write_text("body {}", encoding="utf-8")

    monkeypatch.setattr(resources.sys, "_MEIPASS", str(tmp_path / "_MEIPASS"), raising=False)

    assert resources.static_dir("css", "style.css") == css


def test_user_paths_can_be_redirected_with_home_override(monkeypatch, tmp_path: Path):
    from GONet_Wizard import paths

    monkeypatch.setenv(paths.ENV_HOME, str(tmp_path / "gonet-home"))

    got = paths.cache_dir("dash", "extract_gui")

    assert got == tmp_path / "gonet-home" / "cache" / "dash" / "extract_gui"
    assert got.is_dir()


def test_resource_path_supports_pyinstaller_onedir_layout(monkeypatch, tmp_path: Path):
    from GONet_Wizard import resources

    exe_dir = tmp_path / "dist" / "GONet Wizard"
    bundled = exe_dir / "GONet_Wizard" / "gui" / "templates"
    bundled.mkdir(parents=True)
    template = bundled / "index.html"
    template.write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(resources.sys, "frozen", True, raising=False)
    monkeypatch.delattr(resources.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(resources.sys, "executable", str(exe_dir / "GONet Wizard"), raising=False)

    assert resources.template_dir("index.html") == template


def test_resource_path_supports_macos_app_resources_layout(monkeypatch, tmp_path: Path):
    from GONet_Wizard import resources

    app_root = tmp_path / "GONet Wizard.app" / "Contents"
    macos_dir = app_root / "MacOS"
    resources_dir = app_root / "Resources" / "GONet_Wizard" / "static" / "css"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)
    css = resources_dir / "style.css"
    css.write_text("body {}", encoding="utf-8")

    monkeypatch.setattr(resources.sys, "frozen", True, raising=False)
    monkeypatch.delattr(resources.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(resources.sys, "executable", str(macos_dir / "GONet Wizard"), raising=False)

    assert resources.static_dir("css", "style.css") == css


def test_pyinstaller_build_scaffolding_files_exist():
    root = Path(__file__).resolve().parents[1]
    build_root = root / "build_tools" / "pyinstaller"

    assert (build_root / "README.md").is_file()
    assert (build_root / "gonet_wizard_gui.spec").is_file()
    assert (build_root / "gonet_wizard_cli.spec").is_file()
    assert (build_root / "hooks" / "hook-GONet_Wizard.py").is_file()
    assert (build_root / "_runtime_selection.py").is_file()


def test_pyinstaller_scaffolding_collects_dash_component_package_data():
    root = Path(__file__).resolve().parents[1]
    build_root = root / "build_tools" / "pyinstaller"

    gui_spec = (build_root / "gonet_wizard_gui.spec").read_text(encoding="utf-8")
    cli_spec = (build_root / "gonet_wizard_cli.spec").read_text(encoding="utf-8")
    hook = (build_root / "hooks" / "hook-GONet_Wizard.py").read_text(encoding="utf-8")
    shared = (build_root / "_runtime_selection.py").read_text(encoding="utf-8")

    for text in (gui_spec, cli_spec, hook):
        assert "collect_dash_component_datas" in text

    assert "DASH_COMPONENT_PACKAGES" in shared
    assert '"dash_daq"' in shared
    assert '"dash_extensions"' in shared
    assert "include_py_files=False" in shared


def test_pyinstaller_scaffolding_filters_development_modules_from_runtime_imports():
    root = Path(__file__).resolve().parents[1]
    build_root = root / "build_tools" / "pyinstaller"

    gui_spec = (build_root / "gonet_wizard_gui.spec").read_text(encoding="utf-8")
    cli_spec = (build_root / "gonet_wizard_cli.spec").read_text(encoding="utf-8")
    hook = (build_root / "hooks" / "hook-GONet_Wizard.py").read_text(encoding="utf-8")
    shared = (build_root / "_runtime_selection.py").read_text(encoding="utf-8")

    for text in (gui_spec, cli_spec):
        assert "collect_runtime_hiddenimports" in text
        assert "excludes=EXCLUDES" in text

    assert "excludedimports = EXCLUDES" in hook
    assert "EXCLUDED_MODULE_PREFIXES" in shared
    assert '"kaleido"' in shared
    for module_name in [
        '"dash.testing"',
        '"dash.development.build_process"',
        '"plotly.io._sg_scraper"',
        '"pytest"',
        '"sphinx"',
    ]:
        assert module_name in shared


def test_pyinstaller_scaffolding_keeps_dash_runtime_development_package():
    root = Path(__file__).resolve().parents[1]
    shared = (root / "build_tools" / "pyinstaller" / "_runtime_selection.py").read_text(
        encoding="utf-8"
    )

    assert '"dash.development",' not in shared
    assert '"dash.development.build_process"' in shared


def test_macos_dmg_build_scaffolding_files_exist():
    root = Path(__file__).resolve().parents[1]
    macos_root = root / "build_tools" / "macos"

    assert (macos_root / "README.md").is_file()
    assert (macos_root / "build_dmg.sh").is_file()


def test_macos_dmg_build_script_documents_unsigned_release_flow():
    root = Path(__file__).resolve().parents[1]
    script = (root / "build_tools" / "macos" / "build_dmg.sh").read_text(
        encoding="utf-8"
    )

    assert "hdiutil create" in script
    assert "GONet-Wizard-${SAFE_VERSION}-macOS-${ARCH_NAME}-unsigned.dmg" in script
    assert "--version VERSION" in script
    assert "ln -s /Applications" in script
    assert "README-FIRST.txt" in script
    assert "--skip-pyinstaller" in script
    assert "--force-pyinstaller" in script
