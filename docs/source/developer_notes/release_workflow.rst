Release Workflow
================

This page describes the recommended distribution workflow for packaged GONet
Wizard desktop builds. It focuses on maintainability: source code, build
configuration, and release automation belong in git, while generated installers
belong in GitHub Releases.

For the lower-level PyInstaller and DMG mechanics, see
:doc:`desktop packaging developer notes <packaging>`.

Release Artifacts Are Not Source Files
--------------------------------------

Generated files such as ``.dmg`` and ``.exe`` installers should not be committed
to the repository.

Keep these files in git:

* source code;
* tests;
* documentation;
* PyInstaller specs;
* DMG and future Windows installer scripts;
* GitHub Actions workflows.

Publish these files outside git history:

* macOS DMGs;
* Windows installers;
* checksums;
* other large generated release artifacts.

GitHub Releases are the intended distribution location for user-facing
installers. GitHub Actions artifacts are useful for short-lived test builds,
but they should not be treated as permanent releases.

Recommended Build Cadence
-------------------------

Desktop installers are large and slow to build. They should not be generated on
every commit.

Use this cadence instead:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - When
     - What to run
     - Purpose
   * - Normal code change
     - Unit tests and documentation checks.
     - Keep development fast.
   * - Packaging-related change
     - Local frozen-app smoke test and optional manual GitHub Actions build.
     - Validate packaging logic before merging.
   * - Release candidate
     - Manual GitHub Actions build.
     - Produce a downloadable candidate without publishing a release.
   * - Versioned release
     - Push a ``v*`` tag.
     - Build release artifacts and attach them to a draft GitHub Release.

Local Packaging Test
--------------------

Before asking GitHub Actions to build a release candidate, run the local smoke
test on the relevant operating system.

For macOS:

.. code-block:: bash

   pytest
   rm -rf build dist
   build_tools/macos/build_dmg.sh --force-pyinstaller

Then open the generated DMG, drag ``GONet Wizard.app`` to ``Applications`` or a
temporary test folder, and run the smoke test from
:doc:`desktop packaging developer notes <packaging>`.

Manual GitHub Actions Build
---------------------------

The macOS workflow is designed to be runnable manually from the GitHub Actions
tab. A manual run should:

* build the unsigned macOS DMG on a GitHub-hosted macOS runner;
* generate a SHA-256 checksum file;
* upload a short-lived Actions artifact for testing.

Use manual workflow runs for candidate builds that should be tested before a
tagged release exists.

Tagged Release Build
--------------------

When a version is ready for distribution, create and push a version tag:

.. code-block:: bash

   git tag vX.Y.Z
   git push origin vX.Y.Z

The packaging workflow should build the release artifact and upload it to a
draft GitHub Release for that tag. Keeping the release as a draft provides a
final review step before users see the installer.

A typical release should contain:

.. code-block:: text

   GONet-Wizard-X.Y.Z-macOS-arm64-unsigned.dmg
   SHA256SUMS.txt

When Windows packaging is added, the same release can also contain the Windows
installer:

.. code-block:: text

   GONet-Wizard-X.Y.Z-Windows-x64-Setup.exe

Versioned Artifact Names
------------------------

Release artifacts should include the package version, platform, architecture,
and signing status in the filename.

For example:

.. code-block:: text

   GONet-Wizard-0.3.0-macOS-arm64-unsigned.dmg
   GONet-Wizard-0.3.0-Windows-x64-unsigned-Setup.exe

This makes downloaded files self-describing and avoids ambiguity when several
release candidates are tested side by side.

The macOS DMG script resolves the version from installed package metadata when
possible. For test builds, the version can be overridden manually:

.. code-block:: bash

   build_tools/macos/build_dmg.sh --version 0.3.0-rc1

Checksums
---------

Release workflows should produce a checksum file next to the installer.

For macOS and Linux shell environments:

.. code-block:: bash

   shasum -a 256 dist/GONet-Wizard-*.dmg > dist/SHA256SUMS.txt

Checksums help users and maintainers verify that downloaded files match the
published artifact.

GitHub-Only Distribution
------------------------

For the current project stage, GitHub-only distribution is appropriate:

* source code stays in the repository;
* test builds are uploaded as temporary Actions artifacts;
* official installers are uploaded as GitHub Release assets;
* installers are not committed to git and are not distributed through the Apple App Store or Microsoft Store.

This keeps distribution simple while still allowing repeatable builds and a
clear release history.

User-Facing Install Paths
-------------------------

Release notes and README instructions should keep the installation paths clear:

* the desktop installer or DMG is for GUI users and does not install CLI
  commands;
* the Python package installation is for CLI users, scripted workflows, and
  developers.

A release can contain the desktop DMG without changing the command-line
installation story. If a future release publishes a frozen CLI executable, ship
it as a clearly named separate artifact and document how users should add it to
``PATH``.

macOS Signing Status
--------------------

The current macOS DMG path is explicitly unsigned. Unsigned builds are suitable
for early internal testing and GitHub-only prototypes, but users should expect
macOS Gatekeeper warnings.

Future public-facing macOS releases should consider:

* Developer ID signing;
* hardened runtime settings;
* notarization;
* documenting the difference between signed and unsigned release files.

The filename should continue to include the signing status until signed and
notarized releases are the default.

macOS Architecture Strategy
---------------------------

The first validated macOS path targets Apple Silicon. Intel macOS builds can be
added later as a separate build target if there is user demand.

If both architectures are released, publish separate artifacts with explicit
architecture names, for example:

.. code-block:: text

   GONet-Wizard-0.3.0-macOS-arm64-unsigned.dmg
   GONet-Wizard-0.3.0-macOS-x86_64-unsigned.dmg

Do not label either artifact as universal unless the build process actually
produces and tests a universal binary.

Windows Release Path
--------------------

Windows packaging should follow the same release model:

* validate the frozen executable on Windows;
* wrap it with an installer script, likely Inno Setup;
* account for the WebView2 runtime expectation;
* upload the installer to GitHub Releases;
* avoid committing generated ``.exe`` files to git.

A Windows GitHub Actions workflow can be added after the Windows PyInstaller and
installer path has been validated on a Windows machine or Windows runner.

Release Checklist
-----------------

Before publishing a release:

#. Confirm the version in package metadata.
#. Run the full test suite.
#. Build the platform installer from a clean checkout or clean build directory.
#. Install the generated artifact like a user would.
#. Smoke test launcher, ``show``, ``extract``, and ``dashboard`` from the installed app.
#. Generate checksums.
#. Upload artifacts to a draft GitHub Release.
#. Review release notes, filenames, version numbers, architecture labels, and signing labels.
#. Publish the GitHub Release only after the artifact has been tested.
