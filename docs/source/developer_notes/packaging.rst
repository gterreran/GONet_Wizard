Desktop Packaging
=================

This page describes how GONet Wizard is prepared for frozen desktop builds.
It is intended for maintainers working on packaging, not for end users trying
to analyze GONet data.

The user-facing application remains the same command system described in the
:doc:`command-system developer notes <command_system>`. Packaging adds a
native launch layer around that system so non-terminal users can double-click
``GONet Wizard.app`` on macOS, while advanced users can continue to use the
normal command-line interface.

See also:

* :doc:`UI runtime developer notes <ui_runtime>`
* :doc:`GUI architecture developer notes <gui_architecture>`
* :doc:`release workflow developer notes <release_workflow>`
* :doc:`GUI launcher guide <../gui_guide/launcher>`
* :doc:`CLI Reference <../cli_reference/index>`

Packaging Goals
---------------

Desktop packaging has three goals:

* Keep the GUI as a thin frontend over the existing command system.
* Allow average users to launch GONet Wizard without opening a terminal.
* Preserve all terminal commands for developers, automation, and advanced users.

The frozen desktop app should therefore be an alternate launch path, not a
separate implementation.

Launch Paths
------------

GONet Wizard supports two complementary entry points.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Entry point
     - Typical use
     - Notes
   * - ``GONet_Wizard`` / ``gonet-wizard``
     - Terminal use, scripting, development, and debugging.
     - Dispatches through the normal CLI parser and command handlers.
   * - ``gonet-wizard-gui`` / desktop app bundle
     - Double-click GUI launch for desktop users.
     - Delegates to the same GUI command path used by ``gonet-wizard gui``.

The desktop entry point lives in ``GONet_Wizard/desktop.py``. It exists so
packagers can target a GUI-first executable without changing the terminal CLI.

Key Packaging Code Paths
------------------------

.. list-table::
   :header-rows: 1
   :widths: 42 58

   * - Path
     - Role
   * - ``GONet_Wizard/desktop.py``
     - GUI-first application entry point used by PyInstaller.
   * - ``GONet_Wizard/resources.py``
     - Resolves package-shipped resources from source, installed, and frozen layouts.
   * - ``GONet_Wizard/paths.py``
     - Provides user-writable cache, config, log, data, and temporary directories.
   * - ``GONet_Wizard/gui/server.py``
     - Creates the Flask app and exposes a lightweight ``/health`` endpoint for startup checks.
   * - ``GONet_Wizard/gui/runtime.py``
     - Starts the local UI server and waits for it to respond before opening the webview.
   * - ``build_tools/pyinstaller/``
     - PyInstaller specs, hooks, and runtime-selection rules.
   * - ``build_tools/macos/build_dmg.sh``
     - Creates the unsigned macOS drag-and-drop DMG after the ``.app`` build succeeds.

Resource and Runtime Path Rules
-------------------------------

Frozen apps must not rely on the current working directory being the repository
root. They also must not write cache or runtime data into the installed app
bundle.

Use these helpers instead:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Helper
     - Use it for
   * - ``GONet_Wizard.resources.resource_path()``
     - Read-only package resources such as ``static/``, GUI templates, icons, logos, and small package data files.
   * - ``GONet_Wizard.paths.user_cache_path()``
     - Cache files produced at runtime.
   * - ``GONet_Wizard.paths.user_config_path()``
     - User-specific configuration files.
   * - ``GONet_Wizard.paths.user_log_path()``
     - Log files.
   * - ``GONet_Wizard.paths.user_temp_path()``
     - Temporary files that should not live beside source code or inside the app bundle.

When adding new files that are shipped with the package, make sure they are
available through package data and reachable through ``resources.py``. When
adding files created at runtime, make sure they go through ``paths.py`` or an
explicit user-selected output path.

Startup Readiness
-----------------

The desktop GUI is served by a local Flask application and displayed through
PyWebView. Frozen applications can start more slowly than source-mode runs, so
opening the webview immediately can produce a blank first window.

The packaging-ready startup sequence is:

.. code-block:: text

   start local Flask server
        |
        v
   wait for /health to respond
        |
        v
   open PyWebView window

The health check makes first launch deterministic and should remain part of the
packaged startup path.

PyInstaller Build Files
-----------------------

The PyInstaller configuration lives under ``build_tools/pyinstaller``.

.. list-table::
   :header-rows: 1
   :widths: 42 58

   * - File
     - Purpose
   * - ``gonet_wizard_gui.spec``
     - Builds the GUI-first macOS ``.app`` or Windows GUI executable.
   * - ``gonet_wizard_cli.spec``
     - Builds an optional console executable for CLI testing/distribution.
   * - ``hooks/hook-GONet_Wizard.py``
     - Collects package resources and hidden imports needed by the GONet Wizard package.
   * - ``_runtime_selection.py``
     - Shared include/exclude rules for Dash, Plotly, PyWebView, and other runtime dependencies.

Install build dependencies with:

.. code-block:: bash

   pip install -e ".[build]"

Build the GUI app from the repository root with:

.. code-block:: bash

   python -m PyInstaller build_tools/pyinstaller/gonet_wizard_gui.spec --clean --noconfirm

Build the optional CLI executable with:

.. code-block:: bash

   python -m PyInstaller build_tools/pyinstaller/gonet_wizard_cli.spec --clean --noconfirm

Dash and Plotly Assets
----------------------

Dash applications need more than Python modules. Dash component packages also
serve JavaScript, CSS, JSON metadata, and component bundles directly from their
package directories at runtime.

For this reason, the PyInstaller rules intentionally collect non-Python package
data broadly for Dash-related packages such as ``dash``, ``dash_daq``,
``dash_extensions``, ``dash_core_components``, ``dash_html_components``, and
``dash_table``.

Hidden Python imports are filtered separately through
``build_tools/pyinstaller/_runtime_selection.py``. This avoids restoring broad
``collect_submodules(...)`` calls that would pull obvious development and test
modules into the frozen app.

.. note::

   Some Dash internals have names that sound development- or notebook-specific
   but are still imported during normal Dash startup. For example,
   ``dash.development`` and ``dash._jupyter`` must remain importable even though
   GONet Wizard does not expose Jupyter notebook functionality in the desktop
   app. Keep the narrow Dash shims that Dash imports, while excluding the larger
   notebook ecosystem such as ``IPython``, ``ipykernel``, ``jupyter``,
   ``notebook``, and ``nbconvert``.

Size Cleanup Strategy
---------------------

The packaged app bundles a scientific Python stack, so it will not be tiny.
The cleanup goal is to avoid accidental development baggage without removing
runtime dependencies needed by image processing, Dash apps, Plotly figures, or
PyWebView.

The current strategy is:

* collect required package data broadly for Dash component packages;
* filter hidden imports to avoid test, documentation, gallery, and notebook tooling;
* keep runtime scientific packages unless a concrete test proves they are unused;
* prefer a working app over aggressive size reductions.

If a future frozen build fails with ``ModuleNotFoundError``, add the narrow
runtime module to the include rules instead of reverting to unfiltered package
collection.

Unsigned macOS DMG
------------------

After the raw ``.app`` passes smoke tests, create an unsigned drag-and-drop DMG
for local or GitHub-release testing:

.. code-block:: bash

   build_tools/macos/build_dmg.sh

To force a fresh PyInstaller build first:

.. code-block:: bash

   rm -rf build dist
   build_tools/macos/build_dmg.sh --force-pyinstaller

The default output name is versioned, architecture-specific, and explicitly
marked unsigned:

.. code-block:: text

   dist/GONet-Wizard-<version>-macOS-<arch>-unsigned.dmg

The DMG contains:

* ``GONet Wizard.app``;
* an ``Applications`` shortcut;
* ``README-FIRST.txt`` with notes about unsigned-build launch behavior.

Unsigned DMGs are useful for internal testing and early GitHub-only
distribution, but they are not a substitute for Developer ID signing and
notarization.

Smoke Test Checklist
--------------------

Before publishing a packaging artifact, run a clean build and test the frozen
app, not only the source checkout.

Recommended local test:

.. code-block:: bash

   pytest
   rm -rf build dist
   build_tools/macos/build_dmg.sh --force-pyinstaller

Then install or open the generated app and check:

* the main launcher opens from Finder or from the installed app location;
* the launcher CSS, JavaScript, logo, and templates load correctly;
* the ``show`` form opens and can render an image preview;
* the ``extract`` form opens and can launch the interactive Dash extraction UI;
* the ``dashboard`` command opens the dashboard and loads Dash component assets;
* the app can be closed and reopened without a blank first window;
* runtime cache/log/temp files are not created in the repository root or inside the app bundle.

Troubleshooting Frozen Builds
-----------------------------

Blank window on first launch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This usually means the webview opened before the local Flask server was ready.
Confirm that the GUI runtime starts the server, waits for ``/health``, and only
then opens the webview.

Missing Dash asset
~~~~~~~~~~~~~~~~~~

Errors such as missing ``package-info.json`` or ``*.min.js`` files usually mean
that a Dash component package is missing package data in the PyInstaller rules.
Add package data collection for the component package rather than hard-coding a
single file.

Missing Python module
~~~~~~~~~~~~~~~~~~~~~

Errors such as ``ModuleNotFoundError`` after size cleanup usually mean that the
module was excluded too aggressively. Add the narrow module or package to the
runtime selection rules and rebuild from a clean ``build`` and ``dist``.

macOS Gatekeeper blocks unsigned app
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unsigned builds may be blocked the first time they are opened on another Mac.
For internal testing, users can usually control-click the app and choose
``Open``, or allow it from ``System Settings > Privacy & Security`` after the
first blocked launch. For wider distribution, plan for signing and notarization.

Future Windows Packaging
------------------------

Windows packaging should follow the same architecture:

* keep the Python package and command system unchanged;
* build a GUI executable from the desktop entry point;
* keep the CLI executable available for advanced users;
* wrap the frozen app in a Windows installer rather than committing generated files to git;
* publish installers as GitHub Release assets.

The likely Windows path is a PyInstaller build followed by an Inno Setup
installer. Windows-specific work should be validated on a real Windows machine
or Windows runner before publishing user-facing artifacts.
