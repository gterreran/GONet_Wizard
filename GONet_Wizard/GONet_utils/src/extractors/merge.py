"""
Alignment and merging utilities
===============================

This module provides utilities to *merge* per-extractor results into a single,
canonically ordered accumulator while preserving **per-file alignment by filepath**.
It implements the core logic used by the runner to combine outputs from multiple
extractors that may succeed on different subsets of files.

Overview
--------
- **Canonical file order:** The first per-file extractor to run establishes
  ``data["files"]`` as the canonical filepath order. Subsequent merges align to it.
- **Intersection-based alignment:** When a later extractor returns results for a
  *subset* of files, the accumulator is trimmed to the **intersection** of filepaths
  (inner join). All previously accumulated per-file columns are reindexed or dropped
  to remain consistent.
- **Deterministic behavior:** Intersections are computed deterministically; if there
  is no overlap, the accumulator is reset to an empty per-file result set.


Functions
---------
:func:`.merge_extractor_into_data`
    Merge a single extractor's results into the global data dictionary, enforcing
    alignment by filepath via inner join against the canonical ``data["files"]``.

:func:`._is_per_file`
    Heuristic to detect whether a value is a per-file vector based on its length.

:func:`._build_index`
    Build a mapping from filepaths to their indices within a given list.

:func:`._reindex`
    Reorder a per-file vector from a source index mapping into a target filepath order.


"""

import numpy as np
from typing import Any, Dict, List

def _is_per_file(value: Any, nfiles: int) -> bool:
    """
    Heuristic: a per-file vector has length == nfiles (list/ndarray).

    Parameters
    ----------
    value : :class:`Any`
        The value to check.
    nfiles : :class:`int`
        The expected number of files.

    Returns
    -------
    :class:`bool`
        True if `value` is a per-file vector of length `nfiles`, False otherwise.

    """
    if isinstance(value, (list, np.ndarray)):
        return len(value) == nfiles
    return False

def _build_index(files: List[str]) -> Dict[str, int]:
    """
    Build a mapping from filepath to its index in `files`.
    
    Parameters
    ----------
    files : :class:`list` of :class:`str`
        List of filepaths.
    
    Returns
    -------
    :class:`dict`
        A dictionary mapping each filepath to its index in `files`.
    
    """
    return {fp: i for i, fp in enumerate(files)}

def _reindex(values: List[Any], src_idx: Dict[str, int], dst_files: List[str]) -> List[Any]:
    """
    Reorder `values` (aligned to src_idx order) into `dst_files` order.
    
    Parameters
    ----------
    values : :class:`list`
        List of values aligned to `src_idx`.
    src_idx : :class:`dict`
        Mapping from filepath to index in `values`.
    dst_files : :class:`list`
        Target list of filepaths to align to.
        
    Returns
    -------
    :class:`list`
        Reordered list of values aligned to `dst_files`.
    
    """
    out = []
    for fp in dst_files:
        i = src_idx[fp]
        out.append(values[i])
    return out

def merge_extractor_into_data(
    data: Dict[str, Any],           # accumulator, must contain data["files"] after first per-file extractor
    ext_results: Dict[str, Any],    # one extractor's output dict (includes "files" if per-file outputs)
) -> Dict[str, Any]:
    """
    Merge a single extractor's results into the global `data`, enforcing alignment by filepath.

    Behavior:

        - If this is the first per-file extractor: sets data["files"] from ext_results["files"].
        - Else: intersects file sets, trims existing per-file arrays, and reindexes new ones.

    Parameters
    ----------
    data : :class:`dict`
        Accumulated data dictionary. Must contain `data["files"]` if any prior per-file extractor has run.
    ext_results : :class:`dict`
        Output from a single extractor. May contain `ext_results["files"]` if it has per-file outputs.
    
    Returns
    -------
    :class:`dict`
        Updated `data` dictionary with merged extractor results.
    
    """

    ext_files = list(ext_files)
    ext_idx = _build_index(ext_files)

    if "files" not in data:
        # First per-file extractor sets the canonical order
        data["files"] = ext_files
    else:
        # Intersect canonical with extractor's files
        canon = data["files"]
        common = sorted(set(canon).intersection(ext_files))
        if not common:
            # No overlap → produce empty aligned result set
            data["files"] = []
            # Trim all existing per-file columns to empty
            for k, v in list(data.items()):
                if k == "files":
                    continue
                if _is_per_file(v, len(canon)):
                    data[k] = []
            # Add extractor per-file keys as empty too
            for k, v in ext_results.items():
                if k == "files":
                    continue
                if _is_per_file(v, len(ext_files)):
                    data[k] = []
                else:
                    data[k] = v
            return data

        # Trim previously accumulated per-file columns to `common`
        canon_idx = _build_index(canon)
        mask_idx = [canon_idx[fp] for fp in common]
        for k, v in list(data.items()):
            if k == "files":
                continue
            if _is_per_file(v, len(canon)):
                if isinstance(v, np.ndarray):
                    data[k] = v[mask_idx].tolist()
                else:
                    data[k] = [v[i] for i in mask_idx]
        data["files"] = common  # update canonical files

    # Now insert extractor outputs aligned to the (possibly updated) canonical order
    dst_files = data["files"]
    for k, v in ext_results.items():
        if k == "files":
            continue
        if _is_per_file(v, len(ext_files)):
            data[k] = _reindex(v, ext_idx, dst_files)
        else:
            # scalar/global field
            data[k] = v

    return data