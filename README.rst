.. image:: docs/source/_static/logo.png
   :alt: GONet Wizard Logo
   :height: 100px
   :align: center

GONet Wizard
============

.. image:: https://img.shields.io/badge/docs-latest-blue.svg
   :target: https://gterreran.github.io/GONet_Wizard/
   :alt: Documentation

.. image:: https://img.shields.io/github/v/tag/gterreran/GONet_Wizard?label=version
   :target: https://github.com/gterreran/GONet_Wizard/releases
   :alt: Latest version

.. image:: https://img.shields.io/github/license/gterreran/GONet_Wizard
   :target: https://github.com/gterreran/GONet_Wizard/blob/main/LICENSE
   :alt: License

A modular toolkit for handling, visualizing, and analyzing GONet camera data.  
Includes an interactive Dash dashboard, CLI utilities, and tools for remote interaction with GONet devices.

📖 Documentation: https://gterreran.github.io/GONet_Wizard/

----

Installation
------------

GONet Wizard has two installation paths, depending on how you want to use it.

**Desktop app for GUI users**

Downloadable desktop installers from the
`GitHub Releases page <https://github.com/gterreran/GONet_Wizard/releases>`_
are intended for users who want to launch GONet Wizard by double-clicking the
application icon. The desktop app opens the graphical launcher and does not
install the command-line tools into your shell ``PATH``.

**Python package for CLI users**

If you want to run terminal commands such as ``GONet_Wizard show``,
``GONet_Wizard extract``, or ``GONet_Wizard gui``, install the Python package:

.. code-block:: bash

   pip install git+https://github.com/gterreran/GONet_Wizard.git

It is recommended to first create and activate a clean environment using Python ≥3.10.
See the full `Documentation <https://gterreran.github.io/GONet_Wizard/installation.html>`_
for more installation options, including desktop-app and Windows notes.

----

License
-------

This project is licensed under the MIT License. See the `LICENSE <https://github.com/gterreran/GONet_Wizard/blob/main/LICENSE>`_ file for details.
