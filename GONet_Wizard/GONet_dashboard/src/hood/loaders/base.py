"""
Base Loaders Module
===================

Core loader infrastructure for the GONet dashboard.

This module defines the common base class and registry used by all file-format
loaders (JSON, CSV, and future extensions). Concrete loaders inherit from
:class:`DataSpecLoaderBase` to obtain DATA_SPEC-aware field parsing, and they
register themselves using :func:`register_loader` so that the dispatcher
(:func:`get_loader`) can locate the appropriate loader for any given file.

Classes
-------
:class:`DataSpecLoaderBase`
    Mixin providing DATA_SPEC-driven field parsing for concrete loaders.

Constants
---------
:data:`_NAME_REGISTRY`
    Dictionary mapping loader names (e.g. ``"json"``, ``"csv"``) to loader instances.
:data:`_EXT_REGISTRY`
    Dictionary mapping file extensions (e.g. ``"json"``, ``"csv"``) to loader instances.

Functions
---------
:func:`register_loader`
    Register a concrete loader instance using both its ``name`` and file
    ``extensions``.
:func:`get_loader`
    Resolve and return a loader instance, either by explicit ``kind`` or by
    inferring the appropriate loader from a file's extension.
"""

from __future__ import annotations
from typing import Dict
from pathlib import Path
from GONet_Wizard.GONet_utils import DATA_SPEC
from .schema import compose_parser

class DataSpecLoaderBase:
    """
    Base mixin providing DATA_SPEC-driven field parsing via the
    :meth:`parse_field` method. Concrete loaders subclass this and implement
    a ``load(files)`` method, as well as defining ``name`` and ``extensions``
    attributes to identify themselves.

    """
    
    def __init__(self):
        """
        Pre-build per-field parsers from DATA_SPEC.

        Attributes
        ----------
        _parsers : :class:`dict`
            Dictionary mapping field names to parser functions.

        """
        self._parsers = {k: compose_parser(fld) for k, fld in DATA_SPEC.items()}

    def parse_field(self, key, value):
        """
        Parse a single field value using the pre-built parser.

        Parameters
        ----------
        key : :class:`str`
            The field name.
        value : Any
            The value to parse.

        Returns
        -------
        Any
            The parsed value, or the original value if no parser is found.

        """

        parser = self._parsers.get(key)
        return parser(value) if parser else value



# Two registries:
#  - by loader name (e.g. "json", "csv")
#  - by extension (e.g. "json", "csv")
_NAME_REGISTRY: Dict[str, DataSpecLoaderBase] = {}
_EXT_REGISTRY: Dict[str, DataSpecLoaderBase] = {}


def register_loader(loader: DataSpecLoaderBase) -> None:
    """
    Register a loader instance under its name and extensions.

    Parameters
    ----------
    loader : :class:`DataSpecLoaderBase`
        The loader instance to register.
    
    Returns
    -------
    :class:`None`
        This function does not return a value.

    """
    _NAME_REGISTRY[loader.name.lower()] = loader
    for ext in loader.extensions:
        key = ext.lower().lstrip(".")
        _EXT_REGISTRY[key] = loader


def get_loader(kind: str | None, sample_path: Path) -> DataSpecLoaderBase:
    """
    Resolve a loader from an optional kind or from the file extension.

    Parameters
    ----------
    kind : :class:`str`, optional
        Loader name (e.g. ``"json"`` or ``"csv"``). If ``None``, the loader
        is inferred from the ``sample_path`` extension.
    sample_path : :class:`pathlib.Path`
        A representative file path used for extension inference.

    Returns
    -------
    :class:`DataSpecLoaderBase`
        The matching loader.

    Raises
    ------
    ValueError
        If no suitable loader can be found.

    """
    if kind:
        loader = _NAME_REGISTRY.get(kind.lower())
        if loader is None:
            raise ValueError(f"No loader registered with name '{kind}'.")
        return loader

    ext = sample_path.suffix.lower().lstrip(".")
    loader = _EXT_REGISTRY.get(ext)
    if loader is None:
        raise ValueError(
            f"No loader registered for extension '{ext}'. "
            "Specify 'kind' explicitly or add a loader for this extension."
        )
    return loader
