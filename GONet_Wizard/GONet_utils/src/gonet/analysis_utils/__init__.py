"""
Analysis utility functions for GONet image calibration and preprocessing.

The :mod:`gonet.analysis_utils` package collects higher-level analysis and
correction tools built on top of the core GONet data structures. These utilities
provide convenience methods for common preprocessing steps such as dark
correction, normalization, and background modeling.

**Modules**

- :mod:`.dark_correction` — Functions for overscan and dark-frame subtraction.

"""

from GONet_Wizard.GONet_utils.src.gonet.analysis_utils.dark_correction import remove_overscan