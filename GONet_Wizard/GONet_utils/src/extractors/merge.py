"""
Per-file alignment and extractor-result merging
===============================================

Extractors may produce outputs for all files, a subset of files, or no per-file
outputs at all.  This module defines the merge rules used by the extraction
runner to combine those outputs into a single accumulator without losing
filepath alignment.

The convention is simple: an extractor result that contains per-file values must
also contain a ``"files"`` key listing the filepath associated with each row.
The first per-file extractor establishes the canonical file order.  Later
per-file extractors are inner-joined against that order, trimming previously
stored per-file columns when necessary.

Functions
---------
:func:`.merge_extractor_into_data`
    Merge one extractor output dictionary into the accumulator.
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
    Merge one extractor result dictionary into an aligned accumulator.

    Parameters
    ----------
    data : :class:`dict`
        Mutable accumulator containing fields collected from previous
        extractors.  If a previous per-file extractor has run, it contains a
        canonical ``"files"`` list.
    ext_results : :class:`dict`
        Output from one extractor.  Per-file outputs must include a ``"files"``
        key whose order matches all per-file vectors in ``ext_results``.

    Returns
    -------
    :class:`dict`
        The same ``data`` object, updated in place and returned for convenience.

    Notes
    -----
    Scalar/global fields are copied directly.  Per-file fields are aligned by
    filepath.  When an extractor returns only a subset of the current canonical
    file list, the accumulator is reduced to the intersection of filepaths.
    """
    # Separate scalars from per-file outputs for this extractor
    ext_files = ext_results.get("files", None)

    # Case A: extractor has only scalars (no 'files' key or empty per-file outputs)
    if not ext_files:
        for k, v in ext_results.items():
            if k == "files":
                continue
            data[k] = v
        return data

    # Case B: extractor has per-file outputs

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