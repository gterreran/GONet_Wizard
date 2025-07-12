"""
Retrieve the version of the GONet_Wizard package.

This module provides the `__version__` variable, which automatically
reflects the current version of the installed package using `importlib.metadata`.

Fallback support for Python <3.8 is provided via `importlib_metadata`.

Attributes
----------
__version__ : :class:`str`
    The version string of the installed GONet_Wizard package.

Raises
------
PackageNotFoundError
    If the GONet_Wizard package is not installed or cannot be found in the environment.
"""

from importlib.metadata import version

__version__ = version("GONet_Wizard")