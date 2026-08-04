"""
Dash layout for the interactive extraction GUI.

This module defines the component tree used by the extraction application: file
selection, image display, region controls, extraction options, and the stores
used by callbacks.  It is intentionally limited to structure and component IDs;
visual presentation belongs in the shared CSS assets so the extraction GUI stays
consistent with the rest of the GONet Wizard desktop interface.

The module-level :data:`layout` keeps a compatibility default, while
:func:`create_layout` returns a fresh copy with the latest file list from the
Flask server configuration. Rebuilding the session-specific parts this way
prevents a reused Dash server from showing stale files after a previous
interactive extraction was closed.

Functions
---------
create_layout
    Return a fresh Dash layout using the currently configured extraction files.

Attributes
----------
layout : :class:`dash.development.base_component.Component`
    Compatibility layout assigned at import time. Runtime launches use
    :func:`create_layout` so repeated extraction sessions receive fresh inputs.
"""

import copy
import os

from dash import dcc, html

from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app


data_list = app.server.config.get("data_files")
if data_list:
    files_path = os.path.dirname(data_list[0])
    data_list = [os.path.basename(f) for f in data_list]
    file_to_show = data_list[0]
else:
    files_path = ""
    data_list = []
    file_to_show = None

aspect_ratio = 1520 / 2028

default_bin = 4

gonet_fig = {
    "data": [
        {
            "z": [],
            "type": "heatmap",
        },
        {
            "z": [],
            "colorscale": [
                [0, "rgba(255, 0, 0, 0.4)"],
                [1, "rgba(255, 0, 0, 0.4)"],
            ],
            "type": "heatmap",
            "showscale": False,
            "opacity": 1.0,
        },
    ],
    "layout": {
        "showlegend": False,
        "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
        "xaxis": {"automargin": True, "ticks": "outside", "mirror": True},
        "yaxis": {"automargin": True, "ticks": "outside", "mirror": True},
        "yaxis_scaleanchor": "x",
        "yaxis_scaleratio": aspect_ratio,
        "dragmode": "zoom",
    },
}


layout = dcc.Loading(
    id="loading-wrapper",
    delay_show=150,
    type="circle",
    children=html.Div(
        className="extract-gui",
        children=[
            # Dummy divs.
            html.Div(id="file-loaded"),
            html.Div(id="heatmap-ready-control"),
            html.Div(id="config-done-dummy-div"),
            html.Div(id="dummy-div"),
            # Stores.
            dcc.Store(id="gonet_file"),
            dcc.Store(id="bin", data=default_bin),
            dcc.Store(id="mask", data=[]),
            dcc.Store(id="extracted-values"),
            dcc.Store(id="save-path"),
            dcc.Store(id="drawn-path"),
            dcc.Store(
                id="extraction-params",
                data={
                    "shape": "circle",
                    "x0": None,
                    "y0": None,
                    "param1": None,
                    "param2": None,
                    "start_angle": -180,
                    "end_angle": 180,
                },
            ),
            html.Div(
                className="extract-main",
                children=[
                    html.Div(
                        className="extract-graph-panel",
                        children=[
                            dcc.Graph(
                                id="gonet-image",
                                figure=gonet_fig,
                                className="extract-graph",
                                config={
                                    "responsive": True,
                                    "modeBarButtonsToAdd": [],
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        className="extract-sidebar",
                        children=[
                            html.Div(
                                className="extract-section",
                                children=[
                                    html.H4("Select File:", className="extract-section-title"),
                                    dcc.Dropdown(
                                        id="file-selector",
                                        options=data_list,
                                        value=file_to_show,
                                    ),
                                ],
                            ),
                            html.Div(
                                className="extract-section extract-two-column-section",
                                children=[
                                    html.Div(
                                        className="extract-column extract-column-divider",
                                        children=[
                                            html.H4("Select Channel:", className="extract-section-title"),
                                            dcc.RadioItems(
                                                id="channel-selector",
                                                options=[
                                                    {"label": "Red", "value": "red"},
                                                    {"label": "Green", "value": "green"},
                                                    {"label": "Blue", "value": "blue"},
                                                ],
                                                value="green",
                                                className="extract-radio-list",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="extract-column",
                                        children=[
                                            html.H4("Binning:", className="extract-section-title"),
                                            dcc.RadioItems(
                                                id="binning-selector",
                                                options=[
                                                    {"label": "1×1", "value": "1x1"},
                                                    {"label": "2×2", "value": "2x2"},
                                                    {"label": "4×4", "value": "4x4"},
                                                ],
                                                value=f"{default_bin}x{default_bin}",
                                                className="extract-radio-list",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="extract-section",
                                children=[
                                    html.H4("Select Shape:", className="extract-section-title"),
                                    dcc.RadioItems(
                                        id="shape-selector",
                                        options=[
                                            {"label": "Circle", "value": "circle"},
                                            {"label": "Rectangle", "value": "rectangle"},
                                            {"label": "Annulus", "value": "annulus"},
                                            {"label": "Free Hand", "value": "freehand"},
                                        ],
                                        value="circle",
                                        className="extract-radio-grid",
                                    ),
                                ],
                            ),
                            html.Div(
                                id="shape-options-container",
                                className="extract-section",
                                children=[
                                    html.Div(
                                        id="shape-options",
                                        className="extract-options-panel",
                                        children=[
                                            html.Div(
                                                id="error-banner",
                                                role="alert",
                                                className="extract-error-banner",
                                                **{"aria-live": "polite"},
                                            ),
                                            html.Label("Center (x, y):", className="extract-label"),
                                            html.Div(
                                                className="extract-input-row",
                                                children=[
                                                    html.Div(
                                                        className="extract-half",
                                                        children=dcc.Input(
                                                            id="shape-center-x",
                                                            type="number",
                                                            placeholder="x",
                                                            debounce=True,
                                                        ),
                                                    ),
                                                    html.Div(
                                                        className="extract-half",
                                                        children=dcc.Input(
                                                            id="shape-center-y",
                                                            type="number",
                                                            placeholder="y",
                                                            debounce=True,
                                                        ),
                                                    ),
                                                ],
                                            ),
                                            html.Label(
                                                "Radius:",
                                                id="shape-extra-parameters",
                                                className="extract-label",
                                            ),
                                            html.Div(
                                                className="extract-input-row",
                                                children=[
                                                    html.Div(
                                                        className="extract-half",
                                                        children=dcc.Input(
                                                            id="shape-parameter1",
                                                            type="number",
                                                            placeholder="radius",
                                                            debounce=True,
                                                        ),
                                                    ),
                                                    html.Div(
                                                        id="shape-parameter2-container",
                                                        className="extract-half hidden",
                                                        children=dcc.Input(
                                                            id="shape-parameter2",
                                                            type="number",
                                                            placeholder="",
                                                            debounce=True,
                                                        ),
                                                    ),
                                                ],
                                            ),
                                            html.Label("Angles (deg):", className="extract-label"),
                                            html.Div(
                                                className="extract-input-row",
                                                children=[
                                                    html.Div(
                                                        className="extract-half",
                                                        children=dcc.Input(
                                                            id="shape-sector-start",
                                                            type="number",
                                                            debounce=True,
                                                            value=-180,
                                                        ),
                                                    ),
                                                    html.Div(
                                                        className="extract-half",
                                                        children=dcc.Input(
                                                            id="shape-sector-end",
                                                            type="number",
                                                            debounce=True,
                                                            value=180,
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        id="freehand-options",
                                        className="extract-freehand-options hidden",
                                        children=[
                                            html.P("Draw your region directly on the figure."),
                                            html.Div(
                                                className="extract-button-row",
                                                children=[
                                                    html.Button(
                                                        "Reset",
                                                        id="freehand-reset-button",
                                                        disabled=True,
                                                    ),
                                                    html.Button(
                                                        "Save",
                                                        id="freehand-save-button",
                                                        disabled=True,
                                                    ),
                                                    dcc.Upload(
                                                        id="upload-path",
                                                        children=html.Button(
                                                            "Load",
                                                            id="freehand-load-button",
                                                            n_clicks=0,
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="extract-section extract-stats-section",
                                children=[
                                    html.H4("Extraction values:", className="extract-section-title"),
                                    html.Div(["Total: ", html.Span(0, id="stat-total")]),
                                    html.Div(["Mean: ", html.Span(0, id="stat-mean")]),
                                    html.Div(["Std Dev: ", html.Span(0, id="stat-std")]),
                                    html.Div(["N Pixels: ", html.Span(0, id="stat-npix")]),
                                ],
                            ),
                            html.Div(
                                className="extract-action-bar",
                                children=[
                                    html.Button("Extract", id="extract-button", disabled=True),
                                    html.Button("Exit", id="exit-button", className="danger-button"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
)

def _configured_file_options() -> tuple[list[dict[str, str]], str | None]:
    """Return dropdown options for the currently configured extraction files.

    The option value stores the full path instead of only the basename. This
    keeps callbacks independent of stale module-level directory state and also
    handles multiple files with the same basename in different directories.

    Returns
    -------
    tuple
        ``(options, selected_file)`` where ``options`` is suitable for a Dash
        dropdown and ``selected_file`` is the first configured file path, or
        ``None`` when no files are configured.
    """
    data_files = [str(path) for path in app.server.config.get("data_files") or []]
    file_options = [
        {"label": os.path.basename(path), "value": path}
        for path in data_files
    ]
    selected_file = data_files[0] if data_files else None
    return file_options, selected_file


def _find_component(component, component_id):
    """Return the first Dash component with ``component_id`` in ``component``."""
    if getattr(component, "id", None) == component_id:
        return component

    children = getattr(component, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]

    for child in children:
        found = _find_component(child, component_id)
        if found is not None:
            return found
    return None


def create_layout():
    """Return a fresh Dash layout for the current extraction session.

    Returns
    -------
    :class:`dash.development.base_component.Component`
        Root Dash component tree for the interactive extraction GUI.
    """
    current_layout = copy.deepcopy(layout)
    file_selector = _find_component(current_layout, "file-selector")
    if file_selector is not None:
        file_selector.options, file_selector.value = _configured_file_options()
    return current_layout
