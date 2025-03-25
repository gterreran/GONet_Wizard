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
        html.Div(id='title-container', children=[
            html.H1("GONet Wizard", className="main-title"),
            html.Img(id='logo',src=r'assets/logo.png', alt='logo'),
        ]),
        html.Div(id='dummy-div'),
        dcc.Store(id='data-json'),
        dcc.Store(id='big-points'),
        dcc.Store(id='active-filters', data=[]),
        dcc.Store(id='status-data'),
        html.Div(id='top-container',children=[
            html.Div(className='main-plot', children=[
                    dcc.Graph(id="main-plot", figure = place_holder_main_plot),
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
                html.Div(id = "folder-container", children=[
                    html.Div(className = 'switch-container', children=
                        daq.BooleanSwitch(className='switch', id='fold-time-switch', on=False, disabled=True),
                    ),
                    html.Div(className='switch-label', children = "Fold time axis", id='fold-time-label'),
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
                            daq.BooleanSwitch(className='switch', id='show-filtered-data-switch', on=True),
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