"""
This module defines the structure and metadata for fields used in the extraction process.
It loads field definitions from a YAML file and provides a :class:`Field` class to represent
each field, including its key, label, unit, and aliases.

**Attributes**

DATA_SPEC_PATH : :class:`pathlib.Path`
    Path to the `data_spec.yaml` file containing field definitions.
DATA_SPEC : :class:`dict`
    A dictionary mapping field keys to :class:`Field` objects, representing the
    metadata for each field.

**Classes**

:class:`Field`
    Represents a single named field to extract, including its key, label, unit, and aliases.

Notes
-----
- The `Field` class provides a structured way to manage field metadata, ensuring
  consistency across the extraction process.

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