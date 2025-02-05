from dash import dcc, html
import dash_daq as daq
from . import env


layout = html.Div([
    dcc.Store(id='data-json'),
    dcc.Store(id='big-points'),
    dcc.Store(id='active-filters', data=[]),
    html.Div(id='top-container',children=[
        html.Div(
            dcc.Graph(id="main-plot"),#, figure= px.scatter(x=[0, 1, 2, 3, 4], y=[0, 1, 4, 9, 16])),
            style={'width': '80%','display': 'inline-block'}
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
        ],
        style={'width': '20%','display': 'inline-block'}
        )
    ]),
    html.Div(id='big-filter-container', children=[
        html.Div(id = "folder-container", children=[
            daq.BooleanSwitch(id='fold-time-switch', on=False, style={'display': 'inline-block'}, disabled=True),
            html.Div("Fold time axis", id='fold-time-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
        ]),
        html.Div(id = "shower-container", children=[
            daq.BooleanSwitch(id='show-filtered-data-switch', on=True, style={'display': 'inline-block'}),
            html.Div("Show filtered data", id='show-filtered-data-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
        ]),
        html.Button('Add filter', id='add-filter', n_clicks=0),
        html.Div(id='custom-filter-container', children=[])
    ]),
    html.Div(id='bottom-container',children=[
        dcc.Graph(id="gonet-image",style={'width': '40%', 'display': 'inline-block'}),
        html.Table(id="info-table",style={'width': '40%', 'display': 'inline-block'})
    ])
])