"""Shared PyInstaller collection rules for GONet Wizard builds.

The first working frozen builds intentionally used broad hidden-import
collection for Dash, Plotly, Flask, and pywebview. That was a safe way to prove
that the app could run, but it also pulled in development, testing, notebook,
and documentation helpers that are not part of the desktop runtime.

This module keeps the data collection broad where Dash needs package sidecar
assets, while filtering hidden imports to runtime-oriented modules only.
"""

from __future__ import annotations

from collections.abc import Iterable

from PyInstaller.utils.hooks import (
    can_import_module,
    collect_data_files,
    collect_submodules,
)


GONET_DATA_INCLUDES = [
    "static/**/*",
    "gui/templates/**/*.html",
    "GONet_utils/src/*.yaml",
]

# Dash component packages read package metadata and serve bundled JS/CSS assets
# from their installed package directories at runtime. Keep package data broad;
# the size cleanup below applies to Python hidden imports, not these sidecars.
DASH_COMPONENT_PACKAGES = [
    "dash",
    "dash_daq",
    "dash_extensions",
    "dash_core_components",
    "dash_html_components",
    "dash_table",
]

# Packages for which PyInstaller needs some dynamic-module help. These are
# filtered by ``is_runtime_module`` before being passed as hidden imports.
RUNTIME_HIDDENIMPORT_PACKAGES = [
    "GONet_Wizard",
    "dash",
    "dash_extensions",
    "dash_daq",
    "plotly",
    # Plotly imports Kaleido dynamically when saving static images/PDFs.
    "kaleido",
    # ReportLab is imported lazily when show_meta saves metadata tables to PDF.
    "reportlab",
    "flask",
    "webview",
]

# Modules that were observed to bloat the frozen app or produce irrelevant
# import warnings during broad collection. They are not required by the desktop
# runtime and should stay out of raw GUI/CLI builds.
EXCLUDED_MODULE_PREFIXES = [
    "_pytest",
    # Dash imports dash.development.base_component at runtime, so do not
    # exclude the whole dash.development package. Exclude only the build-time
    # component-generation helpers that caused the original bundle bloat.
    "dash.development._jl_components_generation",
    "dash.development._r_components_generation",
    "dash.development.build_process",
    "dash.development.component_generator",
    "dash.development.update_components",
    "dash.testing",
    # Dash imports dash._jupyter from dash.dash at import time even when
    # notebook integration is never used. Keep the small internal Dash module,
    # but continue excluding actual Jupyter/IPython runtime packages below.
    "docutils",
    "IPython",
    "ipykernel",
    "jupyter",
    "jupyter_client",
    "jupyter_core",
    "myst_parser",
    "nbclient",
    "nbconvert",
    "nbformat",
    "notebook",
    "plotly.conftest",
    "plotly.io._sg_scraper",
    "plotly.matplotlylib.tests",
    "plotly.matplotlylib.mplexporter.tests",
    "pytest",
    "sphinx",
    "sphinx_autodoc_typehints",
    "sphinx_rtd_theme",
    "sphinxcontrib",
    "webview.platforms.android",
]

# ``Analysis(excludes=...)`` uses import-style names. Passing prefixes here is
# still useful because PyInstaller treats excluded package names as roots to skip.
EXCLUDES = sorted(set(EXCLUDED_MODULE_PREFIXES))


def _matches_prefix(name: str, prefix: str) -> bool:
    """Return True if ``name`` is ``prefix`` or a submodule below it."""
    return name == prefix or name.startswith(f"{prefix}.")


def is_runtime_module(name: str) -> bool:
    """Return True if ``name`` should be eligible as a frozen hidden import."""
    if any(_matches_prefix(name, prefix) for prefix in EXCLUDED_MODULE_PREFIXES):
        return False

    parts = set(name.split("."))
    if "tests" in parts or "testing" in parts:
        return False

    if name.endswith(".conftest") or ".conftest." in name:
        return False

    return True


def unique(items: Iterable[str]) -> list[str]:
    """Return items with duplicates removed while preserving first occurrence."""
    return list(dict.fromkeys(items))


def collect_gonet_datas() -> list[tuple[str, str]]:
    """Collect GONet Wizard package data needed by source and frozen GUIs."""
    return collect_data_files("GONet_Wizard", includes=GONET_DATA_INCLUDES)


def collect_dash_component_datas() -> list[tuple[str, str]]:
    """Collect non-Python data files used by Dash component packages."""
    datas: list[tuple[str, str]] = []
    for package in DASH_COMPONENT_PACKAGES:
        if can_import_module(package):
            datas += collect_data_files(package, include_py_files=False)
    return datas


def collect_runtime_submodules(package: str) -> list[str]:
    """Collect runtime hidden imports for a package, excluding dev/test modules."""
    if not can_import_module(package):
        return []

    try:
        return collect_submodules(package, filter=is_runtime_module)
    except TypeError:
        # Older PyInstaller versions did not expose the filter keyword. The
        # project build extra currently asks for PyInstaller >= 6, but this
        # fallback keeps the spec readable if someone tests an older toolchain.
        return [name for name in collect_submodules(package) if is_runtime_module(name)]


def collect_runtime_hiddenimports(
    packages: Iterable[str] = RUNTIME_HIDDENIMPORT_PACKAGES,
) -> list[str]:
    """Collect filtered hidden imports for all runtime packages."""
    hiddenimports: list[str] = []
    for package in packages:
        hiddenimports += collect_runtime_submodules(package)
    return unique(hiddenimports)
