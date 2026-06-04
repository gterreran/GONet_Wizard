"""
Dashboard data and plotting backend.

The ``hood`` package contains the non-layout logic used by the GONet dashboard:
data loading, schema coercion, derived columns, and Plotly figure construction.
It intentionally sits below the Dash callback layer so that most data-handling
code can be tested without running a Dash application.

Subpackages
-----------
:mod:`.loaders`
    File-format loaders and shared post-processing for dashboard data tables.

Submodules
----------
:mod:`.plot`
    Plotly figure construction and trace-update helpers used by dashboard
    callbacks.
"""
