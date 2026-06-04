"""
Field metadata shared by extraction and dashboard workflows.

GONet Wizard stores field definitions in ``data_spec.yaml`` so that serialized
extraction outputs, dashboard labels, plotting units, and legacy aliases remain
consistent across the package.  This module loads that YAML file at import time
and exposes the result as :data:`DATA_SPEC`, a mapping from canonical field keys
to :class:`Field` objects.

The field specification is intentionally lightweight.  It does not perform data
loading by itself; instead, loaders and extractors use it to discover how values
should be named, displayed, grouped, and matched against older output formats.

Attributes
----------
DATA_SPEC_PATH : :class:`pathlib.Path`
    Path to the package-shipped ``data_spec.yaml`` file.
DATA_SPEC : :class:`dict`
    Mapping from canonical field keys to :class:`Field` metadata objects.

Classes
-------
:class:`Field`
    Metadata container describing one extraction/dashboard field.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any

class Field:
    """
    Represents a single named field to extract.

    Parameters
    ----------
    key : str
        Canonical key for the field.
    label : str
        Human-readable label for display or plotting.
    unit : str
        String representation of the unit (for display only).
    aliases : list of str
        List of legacy or alternate field names.
    plottable : bool
        Whether this field should be available for plotting.
    field_type : str
        Type of field, either 'env' (environment) or 'chn' (channel).
    extras : dict
        Additional metadata for loading or processing the field.
        
    """
    def __init__(
        self,
        key: str,
        label: str,
        unit: str,
        aliases: List[str] = [],
        plottable: bool = True,
        field_type: str = "env",
        **extras: Any,
    ):
        """
        Initialize a field metadata object.

        Parameters
        ----------
        key : :class:`str`
            Canonical field key used internally and in serialized outputs.
        label : :class:`str`
            Human-readable label used in plots, tables, or UI controls.
        unit : :class:`str`
            Display unit associated with the field.
        aliases : :class:`list` of :class:`str`, optional
            Alternate or legacy names accepted for the field.
        plottable : :class:`bool`, optional
            Whether the field should be exposed as a plottable quantity.
        field_type : :class:`str`, optional
            Field category. Expected values are ``"env"`` for environmental
            metadata and ``"chn"`` for channel-derived values.
        **extras
            Additional field metadata loaded from ``data_spec.yaml``. The
            ``load`` entry, when present, is stored on :attr:`load`.

        Returns
        -------
        None
        """
        self.key = key
        self.aliases = aliases or []
        self.label = label
        self.unit = unit
        self.plottable = plottable
        self.field_type = field_type  # 'env' or 'chn'
        self.load: Dict[str, Any] = extras.get("load", {}) or {}

# Path to YAML file relative to this script
DATA_SPEC_PATH = Path(__file__).parent / "data_spec.yaml"

# Load and instantiate Field objects
with open(DATA_SPEC_PATH, "r", encoding="utf-8") as f:
    raw_spec = yaml.safe_load(f)

DATA_SPEC = {k: Field(**v) for k, v in raw_spec.items()}