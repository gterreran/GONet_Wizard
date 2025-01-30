from dash import dcc, html
import dash_daq as daq
from . import env


layout = html.Div([
    html.Div(id='dummy'),
    dcc.Store(id='switch'),
    dcc.Store(id='data-json'),
    dcc.Store(id='labels'),
    dcc.Store(id='big-points'),
    html.Div(id='top-container',children=[
        html.Div(
            dcc.Graph(id="main-plot"),#, figure= px.scatter(x=[0, 1, 2, 3, 4], y=[0, 1, 4, 9, 16])),
            style={'width': '80%','display': 'inline-block'}
        ),
        html.Div([
            dcc.Checklist(id="filters", options=[{"label": c, "value": c} for c in env.CHANNELS], value=['green']),
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
    html.Div(id='filter-container', children=[
        html.Div(id = "folder-container", children=[
            daq.BooleanSwitch(id='fold-time-switch', on=False, style={'display': 'inline-block'}),
            html.Div("Fold time axis", id='fold-time-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
        ]),
        html.Div(id = "shower-container", children=[
            daq.BooleanSwitch(id='show-filtered-data-switch', on=True, style={'display': 'inline-block'}),
            html.Div("Show filtered data", id='show-filtered-data-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
        ]),
        html.Div(id = "sun-altitude-container", children=[
            daq.BooleanSwitch(id='sun-switch', on=False, style={'display': 'inline-block'}),
            html.Div("Sun Altitude <=", id='sun-altitude-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
            dcc.Input(id="sun-altitude", type="number", debounce=True, placeholder="-18", style={'display': 'inline-block'})
        ]),
        html.Div(id="moon-container", children=[
            daq.BooleanSwitch(id='moon-switch', on=False, labelPosition="right", style={'display': 'inline-block'}),
            html.Div("Moon Altitude <=", id='moon-altitude-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
            dcc.Input(id="moon-altitude", type="number", debounce=True, placeholder="0", style={'display': 'inline-block'}),
            html.Div('OR',style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
            html.Div("Moon Illumination <=", id='moon-illumination-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
            dcc.Input(id="moon-illumination", type="number", debounce=True, placeholder="0.2", style={'display': 'inline-block'})
        ]),
        html.Div(id = "condition-code-container", children=[
            daq.BooleanSwitch(id='condition-code-switch', on=False, labelPosition="right", style={'display': 'inline-block'}),
            html.Div("Condition Code <=", id='condition-code-label', style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
            dcc.Input(id="condition-code", type="number", debounce=True, placeholder="2", style={'display': 'inline-block'})
        ])
    ]),
    html.Div(id='bottom-container',children=[
        dcc.Graph(id="gonet-image",style={'width': '40%', 'display': 'inline-block'}),
        html.Table(id="info-table",style={'width': '40%', 'display': 'inline-block'})
    ])
])