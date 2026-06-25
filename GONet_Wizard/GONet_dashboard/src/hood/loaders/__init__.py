"""
Loaders package
================

Unified data loading interface for the GONet dashboard.

This package provides a small, extensible framework for turning various
on-disk data products (JSON logs, CSV summaries, etc.) into a single,
tidy :class:`pandas.DataFrame` suitable for plotting and analysis in the
GONet dashboard.

Design philosophy
-----------------
The loaders package is built around a few guiding ideas:

- **Format-agnostic dashboard code**
  The rest of the dashboard should not care whether data comes from JSON,
  CSV, or any other future format. It calls a single function,
  :func:`load_data`, and receives a fully prepared DataFrame plus lists of
  plottable columns.

- **Thin, pluggable file-format loaders**
  Each concrete loader (e.g. JSON, CSV) is responsible only for:
  
  * Reading one or more files of a specific format.
  * Producing a *long/tidy* DataFrame with one row per
    (exposure, channel) pair.
  * Using the shared :class:`~GONet_Wizard.GONet_utils.src.data_spec.DATA_SPEC`
    configuration and coercion logic where appropriate.

  Loaders do **not** compute derived columns (colors, etc.) and do **not**
  assign epoch indices; those are handled centrally.

- **Centralized post-processing**
  Once all format-specific loaders have done their work, this module:

  * Concatenates their DataFrames.
  * Sorts rows by ``filename`` and assigns an integer ``epoch_idx`` so that
    all rows from the same exposure share the same index.
  * Derives color columns (e.g. ``color_rg``, ``color_gb``, ``color_rb``)
    from channel mean counts via :func:`.colors.color_from_channels`.
  * Builds the lists of plottable environment and channel columns based on
    :data:`DATA_SPEC`.

  This keeps the domain logic (how the dashboard wants to see the data)
  separate from the I/O logic (how the data is stored on disk).

Public API
----------
The main entry point for other parts of the dashboard is:

- :func:`load_data(files, kind=None)`
  
  Given an iterable of file paths, this function:
  
  1. Determines the appropriate loader for each file (either from the
     ``kind`` keyword or by file extension).
  2. Delegates to each loader to read and parse its files.
  3. Concatenates the results into a single DataFrame.
  4. Assigns ``epoch_idx`` based on ``filename``.
  5. Expands the DataFrame with derived color columns and computes the
     ``base_columns`` and ``channel_columns`` lists.

Internal helpers
----------------
This module also defines one internal helper that is not intended to be
used directly by dashboard code:

- :func:`_expand_dataframe(df)`
  
  Adds derived color columns, normalizes dtypes, and computes the
  plottable base/channel column name lists from the combined DataFrame.

Submodules
----------
The loaders package is organized into a few small, focused modules:

- :mod:`.base`
  
  Defines the :class:`DataSpecLoaderBase` mixin, which pre-builds per-field
  parsers from :data:`DATA_SPEC` and exposes :meth:`parse_field` for use by
  concrete loaders. It also contains the loader registry and
  :func:`get_loader`, which maps a loader name or file extension to a
  registered loader instance.

- :mod:`.schema`
  
  Houses the coercion and transform functions used to interpret raw values
  according to :data:`DATA_SPEC` (e.g. converting strings to floats,
  datetimes, or "hours of the day"). Exposes :func:`compose_parser`, which
  builds a per-field parser from the DATA_SPEC configuration.

- :mod:`.colors`
  
  Provides :func:`color_from_channels`, a small utility that computes
  color indices (e.g. ``2.5 log10(a/b)``) from channel mean counts with
  robust NaN handling.

- :mod:`.json_loader`
  
  Implements :class:`JsonLoader`, a concrete loader that reads GONet JSON
  logs (lists of epoch dictionaries) and produces a long/tidy DataFrame
  with one row per (epoch, channel). It relies on
  :class:`DataSpecLoaderBase` for field parsing and registers itself with
  the global loader registry at import time.

- :mod:`.csv_loader`
  
  Implements :class:`CsvLoader`, a concrete loader for GONet CSV summary
  files. It interprets per-channel columns of the form
  ``<channel>_<field>`` (e.g. ``red_mean_counts``) and reshapes them into
  long format (unprefixed field names plus a ``channel`` column). Like
  :class:`JsonLoader`, it registers itself with the loader registry when
  imported.

Additional loaders for new file formats can be added by defining a new
loader class in this package, subclassing :class:`DataSpecLoaderBase`,
and registering it via :func:`~.base.register_loader`.
"""

from __future__ import annotations
from typing import Iterable, Tuple, List, Dict
from pathlib import Path

import numpy as np
import pandas as pd

from GONet_Wizard.GONet_utils import DATA_SPEC
from .base import get_loader
from .colors import color_from_channels

# Make sure loaders are registered
from . import json_loader  # noqa: F401
from . import csv_loader   # noqa: F401


def load_data(
    files: Iterable[str],
    kind: str | None = None,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    High-level loader entry point.

    Parameters
    ----------
    files : :class:`collections.abc.Iterable`
        Iterable of file paths to load.
    kind : :class:`str`, optional
        Optional loader key (e.g., ``"json"`` or ``"csv"``). If omitted, the
        loader is inferred separately for each file from its extension.

    Returns
    -------
    :class:`tuple`
        A 3-tuple ``(df, base_columns, channel_columns)``, where:

        - ``df`` is the combined :class:`pandas.DataFrame`.
        - ``base_columns`` is the list of plottable environment columns.
        - ``channel_columns`` is the list of plottable channel columns.

    Raises
    ------
    ValueError
        If no suitable loader can be found for one or more files, or if
        the resulting DataFrame has no 'filename' column.
    """
    paths = [Path(f) for f in files]
    if not paths:
        return pd.DataFrame(), [], []

    # ---- Group files by loader (allow multiple extensions) ------------------
    loader_to_files: Dict[object, List[str]] = {}

    for p in paths:
        loader = get_loader(kind=kind, sample_path=p)
        loader_to_files.setdefault(loader, []).append(str(p))

    # ---- Load each group and concatenate ------------------------------------
    dfs: List[pd.DataFrame] = []
    for loader, group_files in loader_to_files.items():
        df_part = loader.load(group_files)
        if not df_part.empty:
            dfs.append(df_part)

    if not dfs:
        return pd.DataFrame(), [], []

    df = pd.concat(dfs, ignore_index=True)

    if "filename" not in df.columns:
        raise ValueError(
            "Combined DataFrame has no 'filename' column; cannot derive epoch_idx."
        )

    # Sort by filename (and optionally by something else if you like)
    df = df.sort_values("filename").reset_index(drop=True)

    # Assign the same epoch_idx to all rows with the same filename
    codes, _ = pd.factorize(df["filename"], sort=False)
    df["epoch_idx"] = codes.astype(int)

    # Now expand (colors, base/channel lists)
    df, base_cols, chn_cols = _expand_dataframe(df)
    return df, base_cols, chn_cols


def _expand_dataframe(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Add derived columns (colors) and compute base/channel column lists.

    Parameters
    ----------
    df : :class:`pandas.DataFrame`
        Input DataFrame returned by low-level loaders. Must follow:

        - One row per (epoch, channel).
        - Columns include ``"epoch_idx"``, ``"channel"``, and ``"filename"``.
        - If color columns are desired, include ``"mean_counts"``.

    Returns
    -------
    :class:`tuple`
        A 3-tuple ``(df, base_columns, channel_columns)`` with the expanded
        DataFrame and the plottable column name lists.
    """
    # Normalize dtypes
    if "channel" in df.columns:
        df["channel"] = df["channel"].astype("category")

    # Derive colors if possible
    mean_col = "mean_counts"  # or env.MEAN_FIELD if you define one
    if {"epoch_idx", "channel", mean_col}.issubset(df.columns):
        wide = df.pivot_table(
            index="epoch_idx",
            columns="channel",
            values=mean_col,
            aggfunc="first",
            observed=False,
        )

        # ensure RGB columns exist
        for ch in ("red", "green", "blue"):
            if ch not in wide.columns:
                wide[ch] = np.nan

        color_rg = color_from_channels(wide["red"], wide["green"])
        color_gb = color_from_channels(wide["green"], wide["blue"])
        color_rb = color_from_channels(wide["red"], wide["blue"])

        colors = pd.DataFrame(
            {
                "epoch_idx": wide.index,
                "color_rg": color_rg,
                "color_gb": color_gb,
                "color_rb": color_rb,
            }
        )
        df = df.merge(colors, on="epoch_idx", how="left")
    else:
        # add empty color columns for consistency
        for c in ("color_rg", "color_gb", "color_rb"):
            if c not in df.columns:
                df[c] = pd.NA

    # base / channel plottable columns from DATA_SPEC
    base_columns: List[str] = [
        k
        for k, f in DATA_SPEC.items()
        if getattr(f, "field_type", "env") == "env"
        and getattr(f, "plottable", True)
        and k in df.columns
    ]

    channel_columns: List[str] = [
        k
        for k, f in DATA_SPEC.items()
        if getattr(f, "field_type", "env") == "chn"
        and getattr(f, "plottable", True)
        and k in df.columns
    ]

    # add derived colors to base list
    for c in ("color_rg", "color_gb", "color_rb"):
        if c in df.columns and c not in base_columns:
            base_columns.append(c)

    return df, base_columns, channel_columns
