"""
CSV loader for the GONet dashboard.

This module defines :class:`CsvLoader`, a concrete file-format loader for
GONet CSV summary files. Each CSV file is expected to contain one row per
exposure, with:

- Base (environment-level) fields stored as regular columns.
- Per-channel photometric fields stored using prefixed column names such as
  ``red_mean_counts``, ``green_total_counts``, or ``blue_std``.

The loader reshapes these wide-format rows into a long/tidy
:class:`pandas.DataFrame`, producing one row per (epoch, channel) pair. It:

1. Parses base fields using DATA_SPEC-aware coercion via
   :meth:`~.base.DataSpecLoaderBase.parse_field`.
2. Identifies per-channel fields by their ``<channel>_`` prefix.
3. Strips the prefix to produce unprefixed field names that match the JSON loader.
4. Attaches a ``channel`` column identifying the color band.

Derived quantities (e.g. color indices) and the assignment of ``epoch_idx`` are
handled upstream by :func:`load_data` after all loaders have produced their
raw long-format DataFrames.

This loader registers itself with the global loader registry at import time
via :func:`~.base.register_loader`.

Classes
-------
:class:`CsvLoader`
    Concrete loader for GONet CSV summary files. 
    
"""

from __future__ import annotations
from typing import Iterable, Dict, Any, List

import pandas as pd

from GONet_Wizard.GONet_dashboard.src import env
from .base import DataSpecLoaderBase, register_loader


class CsvLoader(DataSpecLoaderBase):
    """
    Loader for GONet CSV summary files.

    The expected format is one where each row is an epoch, with
    base fields (env-level) as columns, and per-channel fields prefixed
    by the channel name (e.g. "red_mean_counts", "green_std_counts", etc.).

    This class inherits from :class:`~.base.DataSpecLoaderBase` and implements
    a ``load(files)`` method that returns a long-format DataFrame with parsed
    base fields, parsed per-channel fields, and a ``channel`` column.

    Attributes
    ----------
    name : str
        The name of the loader ("csv").
    extensions : Tuple[str, ...]
        The file extensions associated with this loader ((".csv",)).

    """

    name = "csv"
    extensions = (".csv",)

    def load(self, files: Iterable[str]) -> pd.DataFrame:
        """
        Load CSV files containing GONet epoch summaries into a long-format
        DataFrame.

        Parameters
        ----------
        files : Iterable[str]
            An iterable of file paths to CSV files containing GONet epoch summaries.

        Returns
        -------
        pd.DataFrame
            A long-format DataFrame with parsed base fields, parsed per-channel fields,
            and a "channel" column.

        """
        rows: List[Dict[str, Any]] = []

        for fp in files:
            # Skip commented glossary lines with `comment="#"`.
            df = pd.read_csv(fp, comment="#")

            # Precompute which columns are base vs channel-specific
            all_cols = list(df.columns)
            base_cols = list(all_cols)

            # For channel-specific columns we expect pattern "<ch>_<field>"
            # where ch is one of env.CHANNELS
            channel_prefixes = {f"{ch}_" for ch in env.CHANNELS}

            # Remove channel-specific columns from base_cols
            for col in all_cols:
                for prefix in channel_prefixes:
                    if col.startswith(prefix):
                        if col in base_cols:
                            base_cols.remove(col)
                        break

            # Iterate over epochs (one CSV row = one epoch)
            for _, row_src in df.iterrows():
                # Build base fields (env-level) and parse via DATA_SPEC
                base_parsed: Dict[str, Any] = {}
                for k in base_cols:
                    base_parsed[k] = self.parse_field(k, row_src[k])

                # For each channel, extract its fields and parse
                for ch in env.CHANNELS:
                    # Collect all columns for this channel (e.g. "red_mean_counts")
                    # and map them to unprefixed field names ("mean_counts").
                    ch_fields: Dict[str, Any] = {}
                    prefix = f"{ch}_"

                    for col in all_cols:
                        if not col.startswith(prefix):
                            continue
                        field_name = col[len(prefix) :]  # drop "red_", "green_", etc.
                        value = row_src[col]
                        ch_fields[field_name] = self.parse_field(field_name, value)

                    # If there are no channel fields for this color, skip it
                    if not ch_fields:
                        continue

                    row_out: Dict[str, Any] = dict(base_parsed)
                    row_out["channel"] = ch
                    row_out.update(ch_fields)

                    rows.append(row_out)

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)


# Register the loader at import time
register_loader(CsvLoader())
