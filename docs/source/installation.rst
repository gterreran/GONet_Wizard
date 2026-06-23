Installation
============

The GONet Wizard package provides tools for analyzing and monitoring data from GONet cameras.  
This guide walks you through setting up the environment and installing the package.

.. contents::
   :local:
   :depth: 2

----

Choosing an installation path
-----------------------------

GONet Wizard can be used as a double-click desktop application, as a Python
command-line package, or both. Choose the installation path that matches how you
plan to work.

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Installation path
     - Best for
     - What it provides
   * - Desktop installer or DMG
     - Users who want to open the graphical interface without using a terminal.
     - A double-click ``GONet Wizard`` app that opens the GUI launcher. It does
       not add ``GONet_Wizard`` or ``gonet-wizard`` commands to your shell
       ``PATH``.
   * - Python package installation with ``pip`` or ``pipx``
     - CLI users, scripted workflows, developers, and users who want both the
       terminal commands and the GUI command.
     - The ``GONet_Wizard`` and ``gonet-wizard`` command-line entry points. The
       GUI can also be started from the terminal with ``GONet_Wizard gui``.

.. important::

   Installing the desktop app is not the same as installing the Python command
   line package. The desktop app is meant to hide the terminal for GUI users. If
   you want terminal commands, install the Python package as described below.

Desktop app installation
------------------------

Desktop installers are distributed through the GitHub Releases page when a
packaged build is available. On macOS, the current packaging path produces a
drag-and-drop DMG containing ``GONet Wizard.app``. After dragging the app to
``Applications``, launch it by double-clicking the icon.

The desktop app opens the GUI launcher. It does not install command-line entry
points, modify shell startup files, or add anything to ``PATH``.

Early macOS DMGs may be unsigned. If macOS blocks the app on first launch, see
the release notes and the ``README-FIRST.txt`` file included in the DMG for the
expected Gatekeeper behavior.

Creating a Python environment
-----------------------------

It is highly recommended to use a **dedicated environment** for GONet Wizard to avoid conflicts with system packages.

You can create one using either `venv` or `conda`.

Using `venv`:

.. code-block:: bash

    python -m venv gonet-env
    source gonet-env/bin/activate  # On Windows: gonet-env\Scripts\activate
    pip install --upgrade pip

Using `conda`:

.. code-block:: bash

    conda create -n gonet-env python=3.10
    conda activate gonet-env

----

Installing from GitHub
----------------------

You can install the latest development version of GONet Wizard directly from GitHub:

.. code-block:: bash

    pip install git+https://github.com/gterreran/GONet_Wizard.git

To install a specific version or tag:

.. code-block:: bash

    pip install git+https://github.com/gterreran/GONet_Wizard.git@v0.9.0

To install from a specific development branch:

.. code-block:: bash

    pip install git+https://github.com/gterreran/GONet_Wizard.git@dev

----

Installing from a local clone
-----------------------------

If you wish to contribute to development or experiment with the source code, perform an **editable install**:

.. code-block:: bash

    git clone https://github.com/gterreran/GONet_Wizard.git
    cd GONet_Wizard
    pip install -e .

This will install the package in-place, so any code changes are immediately reflected.

----

Installation via `pyproject.toml`
---------------------------------

GONet Wizard follows modern Python packaging standards using ``pyproject.toml`` and ``setuptools``.

To build or install the package locally using this configuration:

.. code-block:: bash

    pip install .

Or, for development mode:

.. code-block:: bash

    pip install -e .

You do not need to run ``setup.py`` directly. It exists only for compatibility and delegates to ``pyproject.toml``.

----

.. Required environment variables
.. ------------------------------

.. Some functionality—particularly within the dashboard and remote connection tools—requires certain environment variables to be defined.

.. At a minimum, you should define:

.. - ``GONET_ROOT`` – path to the local GONet data
.. - ``ROOT_EXT`` – optional path to the extended image archive
.. - ``GONET_USER`` – remote SSH user (default is ``pi``)
.. - ``GONET_PASSWORD`` – SSH password for the GONet unit

.. If one of these variables is not defined but is essential for the functionality you are trying to use, **you will be prompted to provide it at runtime**. However, note that variables set this way are only valid for the current session and will not persist.

.. To avoid repeated prompts, it is recommended to set these variables persistently by one of the following methods:

.. **Option 1: Define in a `.env` file**

.. Create a file named `.env` in your project root and add:

.. .. code-block:: ini

..     GONET_ROOT=/path/to/gonet/data
..     GONET_USER=pi
..     GONET_PASSWORD=your_password

.. This file will be automatically loaded if `python-dotenv` is installed (it is included in GONet Wizard’s dependencies).

.. **Option 2: Export directly in your shell**

.. .. code-block:: bash

..     export GONET_ROOT=/path/to/gonet/data
..     export GONET_PASSWORD=your_password

.. Add these lines to your `.bashrc`, `.zshrc`, or equivalent to make them persistent across sessions.

.. **Option 3: Add to a conda environment**

.. If using a conda environment, you can add environment variables by editing the `env` file or manually setting them:

.. To make the variables persist in your environment:

.. .. code-block:: bash

..     conda env config vars set GONET_ROOT=/path/to/gonet/data
..     conda env config vars set GONET_PASSWORD=your_password

.. You must deactivate and reactivate the environment to apply the changes:

.. .. code-block:: bash

..     conda deactivate
..     conda activate gonet-env

.. ----

.. Future PyPI Installation
.. ------------------------

.. GONet Wizard is not yet available on PyPI, but in future releases you will be able to install it using:

.. .. code-block:: bash

..     pip install GONet_Wizard

.. Stay tuned for announcements on the GitHub page:
.. https://github.com/gterreran/GONet_Wizard

.. ----

Installation tips for Windows Users
-----------------------------------

Before installing the GONet Wizard package, ensure that you have both Python and Git installed and accessible from your terminal or command prompt.

Check if Python and Git are installed:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can verify their availability with the following commands:

.. code-block:: bash

   python --version
   git --version

If either command results in a “command not found” error or opens a system prompt, follow the instructions to install them. On some systems, a prompt may appear automatically offering to install the missing component — accept it. This ensures the tools are correctly installed and added to your system’s `PATH`.

If the prompt does not appear, download them from:

- Python: https://www.python.org/downloads/
- Git: https://git-scm.com/downloads

Installing GONet Wizard via pip:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once Python and Git are available, install GONet Wizard directly from GitHub using:

.. code-block:: bash

   pip install git+https://github.com/gterreran/GONet_Wizard.git

.. warning::

   After installation, you may see a message like:

   ``WARNING: The script GONet_Wizard is installed in '/Users/yourname/.local/bin' which is not on PATH.``

   If so, you'll need to add that directory to your system ``PATH``. 

   To permanently add environment variables on Windows:

   1. Press Win + S, search for Environment Variables, and select
   
      `Edit the system environment variables → Environment Variables…`
      
   2. Under User variables, click New.
   3. Enter the variable name (e.g., ``PATH``, ``GONET_ROOT``) and its value (e.g., C:\\Users\\YourName\\gonet\\data).
   4. Repeat for any additional variables (e.g., ``ROOT_EXT``).
   5. Click OK and restart your terminal for the changes to take effect.

These variables will be automatically loaded if you’re running the dashboard or CLI tools.

Run the CLI commands
^^^^^^^^^^^^^^^^^^^^

You are now ready to run any GONet Wizard command from the command line, e.g.:

.. code-block:: bash

    GONet_Wizard gui

----

Troubleshooting
---------------

If you encounter issues during install:

- Try cleaning previous builds:

  .. code-block:: bash

      rm -rf build/ dist/ *.egg-info/

- Ensure your environment is activated and Python ≥ 3.10 is installed
- If installing from GitHub, ensure Git is installed and available in your ``PATH``

For support or to open issues, visit: https://github.com/gterreran/GONet_Wizard/issues
