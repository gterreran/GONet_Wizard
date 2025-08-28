"""
Defines the Dash layout for the GONet extraction GUI.

This module defines the full UI used to visualize a 2D image (heatmap),
select a file/channel, choose a geometric shape (circle, rectangle, annulus,
or freehand), configure shape/sector parameters, view extraction statistics,
and trigger actions (Extract / Exit).


**Notes**

- The file list shows only file names, while the actual path is stored
- The figure uses a fixed aspect ratio matching the expected data shape
  (height/width = 1520/2028) via ``yaxis_scaleanchor`` / ``yaxis_scaleratio``.
- The layout uses a two-column flex container: the graph area on the left
  and a fixed-width sidebar (300px) on the right.
- The sidebar hosts controls (file, channel, shape selectors), shape-specific
  inputs, extraction statistics, and action buttons.
- The figure is initialized with 2 data components, one for the main image and
  one for the overlay. The overlay will mark the pixels used by the masked shape.

"""

import os
from dash import dcc, html
from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app

data_list = app.server.config.get("data_files")
# Extract the directory (assuming all are the same)
if data_list:
    files_path = os.path.dirname(data_list[0])
    # Keep only file names
    data_list = [os.path.basename(f) for f in data_list]
    file_to_show = data_list[0]
else:
    files_path = ''
    data_list = []
    file_to_show = None

aspect_ratio = 1520 / 2028

# Create a placeholder heatmap figure
gonet_fig = {
            'data': [{
                'z': [],
                'type': 'heatmap',
                'shapes':{}
            },
            {
                'z': [],
                'colorscale': [[0, "rgba(255, 0, 0, 0.4)"], [1, "rgba(255, 0, 0, 0.4)"]],  # same color throughout
                'type': 'heatmap',
                'showscale': False,
                'opacity': 1.0,  # full opacity on the red but RGBA gives transparency
            }],
            'layout': {
                'showlegend': False,
                'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0},
                'xaxis': {'automargin': True, 'ticks': "outside", 'mirror': True},
                'yaxis': {'automargin': True, 'ticks': "outside", 'mirror': True},
                'yaxis_scaleanchor':"x",
                'yaxis_scaleratio': aspect_ratio,
                'dragmode': 'zoom'
            },
        }

layout = dcc.Loading(
    id="loading-wrapper",
    delay_show=150, #ms
    type="circle", 
    overlay_style={"visibility":"visible", "filter": "blur(2px)"},
    children=html.Div([
        # Dummy divs.
        html.Div(id='ready-dummy-div'),
        html.Div(id='config-done-dummy-div'),
        html.Div(id='dummy-div'),
        # Stores
        dcc.Store(id='save-path'),
        dcc.Store(id='drawn-path'),
        dcc.Store(
            id='extraction-params',
            data={
                'shape': None,
                'x0': None,
                'y0': None,
                'param1': None,
                'param2': None,
                'start_angle': -180,
                'end_angle': 180,
            },
        ),
        # Heatmap area
        html.Div([
            dcc.Graph(
                id="gonet-image",
                figure=gonet_fig,
                style={
                    "width": "900px",   # Scales with data width
                    "height": "608px"
                },
                config={
                    "responsive": True,
                    "modeBarButtonsToAdd": []
                }
                
            )
        ], style={"flex": 1, "overflow": "hidden"}),

        # Sidebar
        html.Div([
            html.Div([
            html.H4("Select File:"),
            dcc.Dropdown(
                id="file-selector",
                options=data_list,
                value=file_to_show,
                style={"width": "100%"}
            )
        ], style={"padding": "10px", "borderBottom": "1px solid #ccc"}),
            # Channel selector
            html.Div([
                html.H4("Select Channel:"),
                dcc.RadioItems(
                    id="channel-selector",
                    options=[
                        {"label": "Red", "value": "red"},
                        {"label": "Green", "value": "green"},
                        {"label": "Blue", "value": "blue"},
                    ],
                    value="green",
                    labelStyle={"display": "block", "margin": "4px 0"}
                )
            ], style={"padding": "10px", "borderBottom": "1px solid #ccc"}),

            # Shape selector
            html.Div([
                html.H4("Select Shape:"),
                dcc.RadioItems(
                    id="shape-selector",
                    options=[
                        {"label": "Circle", "value": "circle"},
                        {"label": "Rectangle", "value": "rectangle"},
                        {"label": "Annulus", "value": "annulus"},
                        {"label": "Free Hand", "value": "freehand"},
                    ],
                    value="circle",
                    labelStyle={"display": "block", "margin": "4px 0"}
                )
            ], style={"padding": "10px", "borderBottom": "1px solid #ccc"}),

            # Shape-specific controls
            html.Div(id="shape-options-container", children=[
                html.Div([
                    html.Label("Center (x, y):"),
                    dcc.Input(id="shape-center-x", type="number", placeholder="x", debounce=True,
                            style={"marginRight": "5px", "width": "100%"}),
                    dcc.Input(id="shape-center-y", type="number", placeholder="y", debounce=True,
                            style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label(id='shape-extra-parameters'),
                    dcc.Input(id="shape-parameter1", type="number", placeholder="Side 1", debounce=True, style={"width": "100%"}),
                    dcc.Input(id="shape-parameter2", type="number", placeholder="Side 2", debounce=True, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector Start Angle (deg):"),
                    dcc.Input(id="shape-sector-start", type="number", debounce=True,
                            value=-180, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector End Angle (deg):"),
                    dcc.Input(id="shape-sector-end", type="number", debounce=True,
                            value=180, style={"width": "100%"}),
                ], id="shape-options"),

                html.Div([
                    html.P("Draw your region directly on the figure."),

                    html.Div([
                        html.Button("Reset", id="freehand-reset-button", disabled=True, style={"marginRight": "8px"}),
                        html.Button("Save", id="freehand-save-button", disabled=True, style={"marginRight": "8px"}),
                        dcc.Upload(id="upload-path",children=html.Button("Load", id="freehand-load-button", n_clicks=0)),
                    ], style={"marginTop": "10px", "display": "flex", "flexWrap": "wrap"})
                ], id="freehand-options", style={"display": "none"})
            ], style={"padding": "10px", "borderBottom": "1px solid #ccc"}),

            # Extraction stats
            html.Div([
                html.H4("Extraction values:"),
                html.Div(["Total: ", html.Span(id="stat-total")]),
                html.Div(["Mean: ", html.Span(id="stat-mean")]),
                html.Div(["Std Dev: ", html.Span(id="stat-std")]),
                html.Div(["N Pixels: ", html.Span(id="stat-npix")]),
            ], style={"padding": "10px", "flex": 1}),

            # Action buttons at the bottom
            html.Div([
                html.Button("Extract", id="extract-button", style={
                    "padding": "10px 20px",
                    "cursor": "pointer",
                    "marginRight": "10px",
                    "flex": "1"
                }),
                html.Button("Exit", id="exit-button", style={
                    "backgroundColor": "#d9534f",  # Bootstrap red
                    "color": "white",
                    "border": "none",
                    "padding": "10px 20px",
                    "cursor": "pointer",
                    "flex": "1"
                }),
            ], style={
                "display": "flex",
                "justifyContent": "space-between",
                "padding": "10px",
                "borderTop": "1px solid #ccc"
            })
        ], style={
            "width": "300px",
            "height": "100vh",
            "borderLeft": "1px solid #ccc",
            "display": "flex",
            "flexDirection": "column"
        })
    ], style={"display": "flex", "flexDirection": "row", "height": "100vh"})
)
