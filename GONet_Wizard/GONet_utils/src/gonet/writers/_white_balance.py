"""
Shared helpers for resolving white-balance gains used by image writers.

GONet RAW JPEG files normally carry white-balance gains in their parsed EXIF
metadata. Converted TIFF products, arithmetic results, and manually constructed
``GONetFile`` objects may not have that metadata. These helpers keep writer
behavior consistent by accepting explicit red/blue gains while preserving the
metadata-based default for original RAW files.
"""

from __future__ import annotations

from numbers import Real
from typing import Any


def _as_numeric_gain(value: object, label: str) -> float:
    """
    Convert a gain value to ``float`` after validating that it is numeric.

    Parameters
    ----------
    value : object
        Candidate gain value.
    label : str
        Human-readable label used in error messages.

    Returns
    -------
    float
        Validated gain value.

    Raises
    ------
    ValueError
        If ``value`` is not a real numeric value.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a numeric value.")
    return float(value)


def resolve_white_balance_gains(
    image: Any,
    red_gain: float | None = None,
    blue_gain: float | None = None,
) -> tuple[float, float]:
    """
    Resolve red and blue white-balance gains for a GONet image object.

    Explicit gains take precedence over metadata. If no explicit gains are
    supplied, the helper reads ``image.meta['JPEG']['WB']``. This preserves the
    existing default behavior for original GONet RAW JPEG files while allowing
    metadata-free TIFF-loaded images to be white-balanced by passing gains
    directly.

    Parameters
    ----------
    image : object
        Object being written. It is expected to expose a ``meta`` attribute when
        metadata-based white balance is desired.
    red_gain : float, optional
        Manual gain applied to the red channel.
    blue_gain : float, optional
        Manual gain applied to the blue channel.

    Returns
    -------
    tuple of float
        ``(red_gain, blue_gain)`` suitable for multiplying image channels.

    Raises
    ------
    ValueError
        If only one explicit gain is supplied, if either explicit gain is not
        numeric, or if metadata gains are missing or invalid.
    """
    if red_gain is not None or blue_gain is not None:
        if red_gain is None or blue_gain is None:
            raise ValueError(
                "Both red_gain and blue_gain must be provided when using "
                "manual white balance gains."
            )
        return (
            _as_numeric_gain(red_gain, "red_gain"),
            _as_numeric_gain(blue_gain, "blue_gain"),
        )

    meta = getattr(image, "meta", None)
    try:
        metadata_red_gain, metadata_blue_gain = meta["JPEG"]["WB"]
        return (
            _as_numeric_gain(metadata_red_gain, "metadata red gain"),
            _as_numeric_gain(metadata_blue_gain, "metadata blue gain"),
        )
    except Exception as exc:
        raise ValueError(
            "White balance metadata 'WB' is missing or invalid. "
            "Provide both red_gain and blue_gain, or set white_balance=False."
        ) from exc
