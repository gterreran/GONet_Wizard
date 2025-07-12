"""
GONet Wizard Dashboard Layout Definition.

This module defines the full layout of the GONet Wizard web dashboard using `Dash <https://dash.plotly.com/>`_ components.
It includes UI elements for plotting, filtering, exporting, and inspecting data. It also defines
placeholder figures used before user interaction or data loading.

Layout Overview
---------------
- Top Section:

    - Title and logo
    - Graph container for the main scatter plot
    - Dropdowns and switches to select channels, axes, and fold settings
    - Export button to download current filtered data

- Bottom Section:

    - Filter controls for custom and selection-based filters
    - Upload/Save status buttons to persist or restore UI state
    - GONet image preview section for pixel-level inspection

Placeholders
------------
- `place_holder_main_plot` : :class:`dict`
    A blank Plotly figure with an image background to serve as the default main plot display.

- `place_holder_GONet` : :class:`dict`
    A blank figure used for the GONet image display on the lower right panel.

Variables
---------
``layout`` : dash.development.base_component.Component
    The full layout tree of the `Dash <https://dash.plotly.com/>`_ app, including all :dashdoc:`Divs <dash-html-components/div>`, :dashdoc:`Graphs <dash-core-components/graph>`, :dashdoc:`Dropdowns <dash-core-components/dropdown>`,
    :dashdoc:`Stores <dash-core-components/store>`, :dashdoc:`Uploads <dash-core-components/upload>`, :dashdoc:`Buttons <dash-html-components/button>`, and custom components.

Notes
-----

- The layout dynamically interacts with callbacks registered in :mod:`GONet_Wizard.GONet_dashboard.src.callbacks`.
- Styling and visibility are managed primarily through CSS classes and `Dash <https://dash.plotly.com/>`_ DAQ components.

"""

from dash import dcc, html
import dash_daq as daq
from GONet_Wizard.GONet_dashboard.src import env

place_holder_main_plot = {
    "data": [],
    "layout": {
        "xaxis": {"visible": False},
        "yaxis": {"visible": False},
        "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
        "images": [
            {
                "layer": "below",
                "opacity": 1,
                "sizex": 1,
                "sizey": 1,
                "sizing": "stretch",
                "source": "assets/Main-plot-placeholder.png",
                "x": 0,
                "xanchor": "left",
                "xref": "paper",
                "y": 1,
                "yanchor": "top",
                "yref": "paper"
            }
        ],
        "paper_bgcolor": "rgba(0, 0, 0, 0)",
        "plot_bgcolor": "rgba(0, 0, 0, 0)",
        "autosize": True
    }
}

place_holder_GONet = {
    "data": [],
    "layout": {
        "xaxis": {"visible": False},
        "yaxis": {"visible": False},
        "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
        "images": [
            {
                "layer": "below",
                "opacity": 1,
                "sizex": 1,
                "sizey": 1,
                "sizing": "stretch",
                "source": "assets/GONet-placeholder.png",
                "x": 0,
                "xanchor": "left",
                "xref": "paper",
                "y": 1,
                "yanchor": "top",
                "yref": "paper"
            }
        ],
        "paper_bgcolor": "rgba(0, 0, 0, 0)",
        "plot_bgcolor": "rgba(0, 0, 0, 0)",
        "autosize": True
    }
}

layout = dcc.Loading(
    id="loading-wrapper",
    delay_show=150, #ms
    type="circle", 
    overlay_style={"visibility":"visible", "filter": "blur(2px)"},
    children=html.Div([
        dcc.Store(id='data-json'),
        dcc.Store(id='active-filters'),
        dcc.Store(id='status-data'),
        html.Div(id='dummy-div'),
        html.Div(id='title-container', children=[
            html.H1("GONet Wizard", className="main-title"),
            html.Img(id='logo',src=r'assets/logo.png', alt='logo'),
        ]),
        html.Div(id='alert-container', className='alert-box', children=[]),
        html.Div(id='top-container',children=[
            html.Div(className='main-plot', children=[
                    dcc.Graph(
                        id="main-plot",
                        figure = place_holder_main_plot,
                        config={
                            "modeBarButtonsToRemove": ["toImage","zoomIn2d", "zoomOut2d"],
                            "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                            "displaylogo": False
                        }
                    ),
                    html.Div(id='stats-container', children=[
                        html.Table(id="stats-table", children=[html.Tr([html.Td(),html.Td()]),html.Tr([html.Td(),html.Td()])]),
                    ]),
                ],
                id = 'graph-container'
            ),
            html.Div([
                dcc.Checklist(id="channels", options=[{"label": c, "value": c} for c in env.CHANNELS], value=['green']),
                html.Div([
                    "X-axis",
                    dcc.Dropdown(id="x-axis-dropdown"),
                ]),
                html.Div([
                    "Y-axis",
                    dcc.Dropdown(id="y-axis-dropdown"),
                ]),
                html.Div(id = "export-button-container", children=[
                    html.Button('Export current data', id='export-data', n_clicks=0),
                    dcc.Download(id="download-json")
                ])
            ],
            id = 'graph-selector-container'
            )
        ]),
        html.Div(id='bottom-container',children=[
            html.Div(id='big-filter-container', children=[
                html.Button('Save status', id='save-status', n_clicks=0),
                # dcc.Download(id="download-status"),
                #html.Button('Load status', id='load-status', n_clicks=0),
                dcc.Upload(id="upload-status",children=html.Button('Load status', n_clicks=0)),
                #dcc.Upload(id="upload-status"),
                html.Div(id='filter-container', children = [
                    html.Button('Filter selection', id='selection-filter', disabled=True, n_clicks=0),
                    html.Button('Add filter', id='add-filter', n_clicks=0),
                    html.Div(id = "shower-container", children=[
                        html.Div(className = 'switch-container', children=
                            daq.BooleanSwitch(className='switch', id='show-filtered-data-switch', on=True, disabled=True),
                        ),
                        html.Div(className='switch-label', children="Show filtered data", id='show-filtered-data-label'),
                    ]),
                    html.Div(id='custom-filter-container', children=[])
                ])
            ]),
            html.Div(id='gonet-image-container',children=[
                dcc.Graph(id="gonet-image", figure= place_holder_GONet),
                html.Table(id="info-table")
            ])
        ])
    ])
)