"""
Schema coercion helpers for dashboard loaders.

Dashboard input files may contain values as strings, native Python objects, or
serialized timestamps depending on the source format.  This module provides the
small coercion and transform functions used by concrete loaders to normalize
those values before they are combined into a single :class:`pandas.DataFrame`.

The functions are intentionally conservative: failed numeric conversions return
``None`` instead of raising, which lets loaders preserve partially valid rows and
lets the dashboard decide how to handle missing values.

Constants
---------
:data:`COERCERS`
    Mapping from schema names to value coercion functions.
:data:`TRANSFORMS`
    Mapping from schema names to post-coercion transform functions.

Functions
---------
:func:`compose_parser`
    Build a per-field parser from a :class:`~GONet_Wizard.GONet_utils.src.data_spec.Field`.
:func:`parse_hours_of_the_day`
    Parse ``HH:MM:SS`` strings across a configurable day boundary.
"""


from __future__ import annotations
from typing import Any, Callable, Dict, Mapping, Optional
import datetime

from GONet_Wizard.GONet_dashboard.src import env


def parse_hours_of_the_day(t: str, start_of_day: datetime.time) -> datetime.datetime:
    """
    Parse 'HH:MM:SS' into a fixed date, split by a day boundary.

    Parameters
    ----------
    t : :class:`str`
        Time string in 'HH:MM:SS' format.
    start_of_day : :class:`datetime.time`
        Time object representing the start-of-day boundary (e.g. UTC or local).

    Returns
    -------
    :class:`datetime.datetime`
        Datetime object representing the parsed time.
    """
    tt = datetime.datetime.strptime(t, "%H:%M:%S").time()

    if tt > start_of_day:
        return datetime.datetime.fromisoformat(f"2025-01-01T{tt}")
    return datetime.datetime.fromisoformat(f"2025-01-02T{tt}")


def as_is(x: Any) -> Any:
    """
    Identity coercer: returns the input as-is.

    Parameters
    ----------
    x : :class:`Any`
        Input value.

    Returns
    -------
    :class:`Any`
        The same input value.
    
    """
    return x


def as_float(x: Any) -> Optional[float]:
    """
    Coerce input to float, or return None if conversion fails.

    Parameters
    ----------
    x : :class:`Any`
        Input value.

    Returns
    -------
    :class:`Optional[float]`
        Float value or None if conversion is not possible.

    """
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def as_int(x: Any) -> Optional[int]:
    """
    Coerce input to int, or return None if conversion fails.

    Parameters
    ----------
    x : :class:`Any`
        Input value.

    Returns
    -------
    :class:`Optional[int]`
        Int value or None if conversion is not possible.

    """
    if x is None:
        return None
    try:
        return int(x)
    except Exception:
        return None


def as_bool(x: Any) -> Optional[bool]:
    """
    Coerce input to bool, or return None if conversion fails.

    Parameters
    ----------
    x : :class:`Any`
        Input value.

    Returns
    -------
    :class:`Optional[bool]`
        Bool value or None if conversion is not possible.

    """
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "f", "no", "n", "off"}:
        return False
    return None


def as_str(x: Any) -> Optional[str]:
    """
    Coerce input to str, or return None if input is None.

    Parameters
    ----------
    x : :class:`Any`
        Input value.
    
    Returns
    -------
    :class:`Optional[str]`
        String value or None if input is None.
    
    """
    if x is None:
        return None
    return str(x)


def as_datetime(x: Any) -> Optional[datetime.datetime]:
    """
    Coerce input to datetime, or return None if conversion fails.

    Parameters
    ----------
    x : :class:`Any`
        Input value.

    Returns
    -------
    :class:`Optional[datetime.datetime]`
        Datetime value or None if conversion is not possible.

    """
    if x is None:
        return None
    if isinstance(x, datetime.datetime):
        return x
    if isinstance(x, str):
        try:
            return datetime.datetime.fromisoformat(x)
        except Exception:
            return None
    return None


COERCERS: Dict[str, Callable[[Any], Any]] = {
    "identity": as_is,
    "float": as_float,
    "int": as_int,
    "bool": as_bool,
    "str": as_str,
    "datetime": as_datetime,
}

TRANSFORMS: Dict[str, Callable[[Any, Mapping[str, Any]], Any]] = {
    "utc_datetime": lambda x, cfg: parse_hours_of_the_day(x, env.DAY_START_UTC),
    "local_datetime": lambda x, cfg: parse_hours_of_the_day(x, env.DAY_START_LOCAL),
}


def compose_parser(field) -> Callable[[Any], Any]:
    """
    Compose a per-field parser from DATA_SPEC.load:
    value -> coerce(value) -> transform(value, cfg)

    Parameters
    ----------
    field : :class:`Any`
        Field definition with optional 'load' configuration.
    
    Returns
    -------
    :class:`Callable[[Any], Any]`
        Parser function that applies coercion and transformation.
    
    """
    cfg = getattr(field, "load", {}) or {}
    coerce_name = str(cfg.get("coerce", "")).strip().lower()
    xform_name = str(cfg.get("transform", "")).strip().lower()

    coerce = COERCERS.get(coerce_name, lambda x: x) if coerce_name else (lambda x: x)
    xform = TRANSFORMS.get(xform_name) if xform_name else None

    if xform is None:
        def parser(v, _coerce=coerce):
            try:
                return _coerce(v)
            except Exception:
                return None

        return parser

    def parser(v, _coerce=coerce, _xform=xform, _cfg=cfg):
        try:
            v2 = _coerce(v)
        except Exception:
            return None
        try:
            return _xform(v2, _cfg)
        except Exception:
            return None

    return parser
