"""
Retrieve the version of the GONet_Wizard package.

This module provides the `__version__` variable, which automatically
reflects the current version of the installed package using `importlib.metadata`.

Fallback support for Python <3.8 is provided via `importlib_metadata`.

Attributes
----------
__version__ : :class:`str`
    The version string of the installed GONet_Wizard package.

Notes
-----
- The version is determined at runtime, so it will reflect the actual installed
  version of the package. If the package is not installed, it defaults to "dev".

"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("GONet_Wizard")
except PackageNotFoundError:
    __version__ = "dev"