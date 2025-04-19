============
GONet Wizard
============

.. image:: https://img.shields.io/github/v/tag/gterreran/GONet_Wizard?label=version&color=blue
   :target: https://github.com/gterreran/GONet_Wizard/tags
   :alt: GitHub latest tag

.. automodule:: GONet_Wizard
   :members:
   :undoc-members:
   :show-inheritance:

See the :doc:`installation` page for details on how to install the package.

See the :doc:`CLI <cli>` page a description on how to use some of the functionalities from the command line.

The following modules are included in the GONet Wizard package:

- :mod:`GONet_Wizard.GONet_dashboard`
- :mod:`GONet_Wizard.GONet_utils`
- :mod:`GONet_Wizard.commands`

Each module is documented in its own section below.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   cli
   GONet_dashboard
   GONet_utils
   commands
   Changelog <https://github.com/gterreran/GONet_Wizard/blob/main/CHANGELOG.md>


Versioning
==========

The GONet Wizard project uses **Git-based versioning** powered by `setuptools_scm <https://github.com/pypa/setuptools_scm>`_.
The version is defined by :mod:`_version` and can be retrieved accessing the ``__version__`` attribute of the :mod:`GONet_Wizard` package or by running:

.. code-block:: bash

   GONet_Wizard --version


Changelog
=========

The full `changelong <https://github.com/gterreran/GONet_Wizard/blob/main/CHANGELOG.md>`_ is available on GitHub:

The project uses `git-changelog <https://github.com/pawamoy/git-changelog>`_ to automatically generate a structured changelog from the commit history and Git tags.