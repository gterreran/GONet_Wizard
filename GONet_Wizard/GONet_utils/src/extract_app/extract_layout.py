"""
Defines the Dash layout for the GONet extraction GUI.

The layout intentionally keeps visual styling in the shared CSS file. Dash
components are annotated with IDs and CSS classes only, so the extraction GUI
can share the same visual language as the rest of GONet Wizard.
"""

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
                    "shape": None,
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
                                                "Parameters",
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
                                                            placeholder="Side 1",
                                                            debounce=True,
                                                        ),
                                                    ),
                                                    html.Div(
                                                        id="shape-parameter2-container",
                                                        className="extract-half",
                                                        children=dcc.Input(
                                                            id="shape-parameter2",
                                                            type="number",
                                                            placeholder="Side 2",
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
                                    html.Button("Extract", id="extract-button"),
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
