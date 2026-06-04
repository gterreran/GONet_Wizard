"""
Internal utility implementation package.

This package contains the implementation modules that back the public
:mod:`GONet_Wizard.GONet_utils` namespace.  Most users should import through
``GONet_Wizard.GONet_utils`` or through the command-line interface rather than
from this package directly.

Subpackages
-----------
:mod:`.gonet`
    Core image containers, parsers, writers, and image-processing utilities.
:mod:`.extractors`
    Small extractor objects and runners used to build structured extraction
    outputs from GONet files and regions.
:mod:`.extract_app`
    Dash-based interactive extraction GUI.
:mod:`.data_spec`
    Field metadata loaded from ``data_spec.yaml`` and shared by extraction and
    dashboard code.
"""
