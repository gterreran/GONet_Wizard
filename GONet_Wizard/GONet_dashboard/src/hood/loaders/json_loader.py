"""
JSON loader for the GONet dashboard
=======================================

This module defines the :class:`JsonLoader`, a concrete file-format loader that
reads GONet JSON data products. Each JSON file is expected to contain a list of
epoch dictionaries, with top-level metadata fields and per-channel subdicts
(e.g. ``{"red": {...}, "green": {...}, "blue": {...}}``). The loader reshapes
these records into a long/tidy :class:`pandas.DataFrame` where each row
corresponds to a single (epoch, channel) pair.

Field values are parsed using the DATA_SPEC-driven coercion and transformation
logic provided by :class:`~.base.DataSpecLoaderBase`. This loader does not
compute derived quantities (e.g. color indices) and does not assign epoch
indices—those steps are handled at the package level by :func:`load_data`.

The loader registers itself at import time using
:func:`~.base.register_loader`, making it discoverable by the loader
dispatcher.

Classes
-------
:class:`JsonLoader`
    Loader for JSON files where each file is a list of epoch dicts.
    
"""


from __future__ import annotations
from typing import Iterable, Dict, Any, List

import json
import pandas as pd

from GONet_Wizard.GONet_dashboard.src import env
from .base import DataSpecLoaderBase, register_loader



class JsonLoader(DataSpecLoaderBase):
    """
    Concrete loader for JSON epoch lists. Inherits from
    :class:`~.base.DataSpecLoaderBase` and implements a ``load(files)``
    method that returns a long-format DataFrame with parsed base fields,
    parsed per-channel fields, and a ``channel`` column.

    Attributes
    ----------
    name : str
        The name of the loader ("json").
    extensions : Tuple[str, ...]
        The file extensions associated with this loader ((".json",)).

    """

    name = "json"
    extensions = (".json",)

    # Protocol: load(self, files) -> DataFrame
    def load(self, files: Iterable[str]) -> pd.DataFrame:
        """
        Load JSON files containing lists of epoch dicts into a long-format
        DataFrame.

        Parameters
        ----------
        files : Iterable[str]
            An iterable of file paths to JSON files containing lists of epoch dicts.

        Returns
        -------
        pd.DataFrame
            A long-format DataFrame with parsed base fields, parsed per-channel fields,
            and a "channel" column.

        """

        rows: List[Dict[str, Any]] = []

        for fp in files:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError(f"{fp} does not contain a list of epoch records")

            for epoch in data:
                # separate base vs channel dicts
                ch_dicts = {
                    ch: epoch[ch]
                    for ch in env.CHANNELS
                    if ch in epoch and isinstance(epoch[ch], dict)
                }
                base_raw = {k: v for k, v in epoch.items() if k not in env.CHANNELS}

                if not ch_dicts:
                    continue

                # parse base fields
                base_parsed = {k: self.parse_field(k, v) for k, v in base_raw.items()}

                # one row per channel
                for ch, cd in ch_dicts.items():
                    row = dict(base_parsed)
                    row["channel"] = ch
                    for k, v in cd.items():
                        # 👇 this was `row[k] = row[k] = ...` before
                        row[k] = self.parse_field(k, v)
                    rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        return df



# Register the loader at import time
register_loader(JsonLoader())
