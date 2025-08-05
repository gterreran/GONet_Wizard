"""
Defines the Dash layout for the GONet extraction GUI.

This module defines the full UI used to visualize a 2D image (heatmap),
select a file/channel, choose a geometric shape (circle, rectangle, annulus,
or freehand), configure shape/sector parameters, view extraction statistics,
and trigger actions (Extract / Exit).


**Notes**

- The figure uses a fixed aspect ratio matching the expected data shape
  (height/width = 1520/2028) via ``yaxis_scaleanchor`` / ``yaxis_scaleratio``.
- The layout uses a two-column flex container: the graph area on the left
  and a fixed-width sidebar (300px) on the right.
- The sidebar hosts controls (file, channel, shape selectors), shape-specific
  inputs, extraction statistics, and action buttons.
    
"""

from dash import dcc, html
from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app

data_list = app.server.config.get("data_files", ['------'])

aspect_ratio = 1520 / 2028

# Create a placeholder heatmap figure
gonet_fig = {
            'data': [{
                'z': [],
                'type': 'heatmap',
                'shapes':{}
            }],
            'layout': {
                'showlegend': False,
                'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0},
                'xaxis': {'automargin': True, 'ticks': "outside", 'mirror': True},
                'yaxis': {'automargin': True, 'ticks': "outside", 'mirror': True},
                'yaxis_scaleanchor':"x",
                'yaxis_scaleratio': aspect_ratio,
            },
        }

layout = dcc.Loading(
    id="loading-wrapper",
    delay_show=150, #ms
    type="circle", 
    overlay_style={"visibility":"visible", "filter": "blur(2px)"},
    children=html.Div([
        dcc.Store(id='save-path'),
        dcc.Store(id='load-path'),
        html.Div(id='dummy-div'),
        # Heatmap area
        html.Div([
            dcc.Graph(
                id="gonet_image",
                figure=gonet_fig,
                style={
                    # "height": "100vh",
                    # "width": "100%",
                    # "paddingBottom": f"{aspect_ratio * 100}%",  # CSS trick
                    # "position": "relative",
                    "width": "900px",   # Scales with data width
                    "height": "608px"
                },
                config={"responsive": True}
            )
        ], style={"flex": 1, "overflow": "hidden"}),

        # Sidebar
        html.Div([
            html.Div([
            html.H4("Select File:"),
            dcc.Dropdown(
                id="file-selector",
                options=data_list,
                value=data_list[0],
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
                    dcc.Input(id="circle-center-x", type="number", placeholder="x", debounce=True,
                            style={"marginRight": "5px", "width": "100%"}),
                    dcc.Input(id="circle-center-y", type="number", placeholder="y", debounce=True,
                            style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Radius:"),
                    dcc.Input(id="circle-radius", type="number", placeholder="radius", debounce=True,
                            style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector Start Angle (deg):"),
                    dcc.Input(id="circle-sector-start", type="number", debounce=True,
                            value=-180, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector End Angle (deg):"),
                    dcc.Input(id="circle-sector-end", type="number", debounce=True,
                            value=180, style={"width": "100%"}),
                ], id="circle-options"),

                html.Div([
                    html.Label("Center (x, y):"),
                    dcc.Input(id="rectangle-center-x", type="number", placeholder="x", debounce=True, style={"marginRight": "5px", "width": "100%"}),
                    dcc.Input(id="rectangle-center-y", type="number", placeholder="y", debounce=True, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Side 1, Side 2:"),
                    dcc.Input(id="rectangle-side1", type="number", placeholder="Side 1", debounce=True, style={"width": "100%"}),
                    dcc.Input(id="rectangle-side2", type="number", placeholder="Side 2", debounce=True, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector Start Angle (deg):"),
                    dcc.Input(id="rectangle-sector-start", type="number", debounce=True,
                            value=-180, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector End Angle (deg):"),
                    dcc.Input(id="rectangle-sector-end", type="number", debounce=True,
                            value=180, style={"width": "100%"}),
                ], id="rectangle-options", style={"display": "none"}),

                html.Div([
                    html.Label("Center (x, y):"),
                    dcc.Input(id="annulus-center-x", type="number", placeholder="x", debounce=True, style={"marginRight": "5px", "width": "100%"}),
                    dcc.Input(id="annulus-center-y", type="number", placeholder="y", debounce=True, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Outer Radius:"),
                    dcc.Input(id="annulus-outer-radius", type="number", placeholder="radius", debounce=True, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Inner Radius:"),
                    dcc.Input(id="annulus-inner-width", type="number", placeholder="width", debounce=True, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector Start Angle (deg):"),
                    dcc.Input(id="annulus-sector-start", type="number", debounce=True,
                            value=-180, style={"width": "100%"}),
                    html.Br(), html.Br(),
                    html.Label("Sector End Angle (deg):"),
                    dcc.Input(id="annulus-sector-end", type="number", debounce=True,
                            value=180, style={"width": "100%"}),
                ], id="annulus-options", style={"display": "none"}),

                html.Div([
                    dcc.Store("freehand-path", data = []),
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
