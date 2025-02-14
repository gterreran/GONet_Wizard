import inspect, datetime
import numpy as np
from . import env
import operator
from dash import html, dcc, html
import dash_daq as daq

op = {
    '<': operator.lt ,
    '<=': operator.le ,
    '=': operator.eq ,
    '!=': operator.ne ,
    '=>': operator.ge ,
    '>': operator.gt ,
}

def debug():
    '''
    This is just for debuggin purposes.
    It prints the function in which it is called,
    and the line at which it is called.
    '''

    print(
        '{} fired. Line {}.'.format(
            inspect.stack()[1][3],
            inspect.stack()[1][2]))

def sort_figure(fig):
    new_order = []
    for img in fig['data']:
        if img['filtered'] and not img['big_point']:
            new_order.append(img)
    for img in fig['data']:
        if not img['filtered'] and not img['big_point']:
            new_order.append(img)
    for img in fig['data']:
        if img['big_point']:
            new_order.append(img)
    
    fig['data'] = new_order[:]
    return fig

def get_labels(fig):
    return {'x': fig['layout']['xaxis']['title']['text'], 'y': fig['layout']['yaxis']['title']['text']}

def plot_scatter(all_data, channels, fig, active_filters, show_filtered_points, fold_switch):

    labels = get_labels(fig)

    channel_filter = {}
    if labels['x'] in env.LABELS['gen'] and labels['y'] in env.LABELS['gen']:
        channel_filter['gen'] = np.array(all_data['channel']) == 'red'
    else:
        for c in channels:
            channel_filter[c] = np.array(all_data['channel']) == c
    
    filters = []

    for f in active_filters:
        if 'secondary' not in f:
            filters.append(op[f['operator']](np.array(all_data[f['label']]),type(all_data[f['label']][0])(f['value'])))
        else:
            filters.append(np.logical_or(op[f['operator']](np.array(all_data[f['label']]),type(all_data[f['label']][0])(f['value'])), op[f['secondary']['operator']](np.array(all_data[f['secondary']['label']]),type(all_data[f['secondary']['label']][0])(f['secondary']['value']))))

    total_filter = np.full(len(all_data['channel']), True)
    for f in filters:
        total_filter = np.logical_and(total_filter,f)

    if labels['x'] == 'date' and fold_switch:
        time = []
        for t in all_data[labels['x']]:
            if datetime.datetime.fromisoformat(t).time()>env.DAY_START:
                time.append('2025-01-01T'+t.split('T')[1])
            else:
                time.append('2025-01-02T'+t.split('T')[1])
        x_data = np.array(time)
        fig['layout']['xaxis']['tickformat'] = "%H:%M"
    else:
        x_data = np.array(all_data[labels['x']])
        # if 'tickformat' in fig['layout']['xaxis']:
        #     del fig['layout']['xaxis']['tickformat']
    y_data = np.array(all_data[labels['y']])
    real_idx = np.array(all_data['idx'])

    for c in channel_filter:
        selected_data_filter = np.logical_and(total_filter, channel_filter[c])
        fig['data'].append({
            'hovertemplate': labels['x']+'=%{x}<br>'+labels['y']+'=%{y}',
            'x': x_data[selected_data_filter],
            'y': y_data[selected_data_filter],
            'type': 'scatter',
            'mode': 'markers',
            'marker': {
                'color': env.COLORS[c](1),
                'symbol': 'circle'
            },
            'channel': c,
            'showlegend': True,
            'idx': real_idx[selected_data_filter],
            'filtered': False,
            'hidden': False,
            'big_point': False
        })
        filtered_out_data = np.logical_and(~total_filter, channel_filter[c])
        if len(x_data[filtered_out_data])>0:
            fig['data'].append({
                'hovertemplate': labels['x']+'=%{x}<br>'+labels['y']+'=%{y}',
                'x': x_data[filtered_out_data],
                'y': y_data[filtered_out_data],
                'type': 'scatter',
                'mode': 'markers',
                'marker': {
                    'color': env.COLORS[c](0.2) if show_filtered_points else env.COLORS[c](0),
                    'symbol': 'circle'
                }, 
                'channel': c,
                'showlegend': True,
                'idx': real_idx[filtered_out_data],
                'filtered': True,
                'hidden': not show_filtered_points,
                'big_point': False
            })

    return fig

def plot_big_points(data, idx_big_point, fig, fold_switch):

    labels = get_labels(fig)

    # Big point in main figure
    big_point_figs = []

    idx_epoch = data['idx'][idx_big_point]
    points = np.array(data['idx']) == idx_epoch

    for i,img in reversed(list(enumerate(fig['data']))):
        # Removing eventual big points
        if img['big_point']:
            fig['data'].pop(i)
            continue

        if idx_epoch not in img['idx']:
            continue

        if img['channel'] == 'gen':
            channel = 'green'
        else:
            channel = img['channel']

        selected_data_filter = np.logical_and(points, np.array(data['channel']) == channel)

        x_data = np.array(data[labels['x']])[selected_data_filter]
        y_data = np.array(data[labels['y']])[selected_data_filter]

        if labels['x'] == 'date' and fold_switch:
            if datetime.datetime.fromisoformat(x_data[0]).time()>env.DAY_START:
                x_data = ['2025-01-01T'+x_data[0].split('T')[1]]
            else:
                x_data = ['2025-01-02T'+x_data[0].split('T')[1]]

        big_point_figs.append({
            'x': x_data,
            'y': y_data,
            'type': 'scatter',
            'mode': 'markers',
            'marker': {
                'color': img['marker']['color'],
                'symbol': 'circle',
                'size': 15,
                'line':{
                    'width':0 if img['hidden'] else 2,
                    'color':'DarkSlateGrey'
                }
            },
            'channel': img['channel'],
            'showlegend': False,
            'filtered': img['filtered'],
            'hidden':img['hidden'],
            'big_point': True
        })

    fig['data'] = fig['data'] + big_point_figs

    return fig

def get_stats(fig):

    labels = get_labels(fig)

    data_figs = {img['channel']:img for img in fig['data'] if not img['filtered'] and not img['big_point']}

    stats_table = {}

    for axis in ['x','y']:
        stats_table[axis] = []
        try:
            if labels[axis] in env.LABELS['gen']:
                stats_table[axis].append({'label':labels[axis]})
                if 'gen' in data_figs:
                    m = np.mean(data_figs['gen'][axis])
                    s = np.std(data_figs['gen'][axis])
                else:
                    m = np.mean(data_figs[list(data_figs.keys())[0]][axis])
                    s = np.std(data_figs[list(data_figs.keys())[0]][axis])

                stats_table[axis][-1]['value'] = f"{m:.2f} ± {s:.2f}"

            else:
                for c in env.CHANNELS:
                    if c in data_figs:
                        stats_table[axis].append({
                            'label': f"{labels[axis]}_{c}",
                            'value': f"{np.mean(data_figs[c][axis]):.2f} ± {np.std(data_figs[c][axis]):.2f}"
                        })
        except np.core._exceptions._UFuncNoLoopError:
            stats_table[axis]=[]

    formatted_stats_table = [html.Tr([html.Td(el[val],style={'width':'200px','border':'1px solid black'}) for el in stats_table[axis] for val in ['label', 'value']], style={'border':'1px solid black'}) for axis in ['x', 'y']]

    return formatted_stats_table


def new_empty_filter(idx, labels):

    new_filter = html.Div(id = {"type":'filter-container', "index":idx}, children=[
                html.Div(id = {"type":'first-filter-container', "index":idx}, children=[
                    daq.BooleanSwitch(id={"type":'filter-switch', "index":idx}, on=False, style={'display': 'inline-block'}),
                    dcc.Dropdown(id={"type":'filter-dropdown', "index":idx}, options=labels, style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px', 'width':'200px'}),
                    dcc.Dropdown(id={"type":'filter-operator', "index":idx}, options=['<','<=','=','!=','=>','>'], value = '<=', style={'display': 'inline-block', 'margin-left':'5px', 'margin-right':'5px', 'width':'40px'}),
                    dcc.Input(id={"type":'filter-value', "index":idx}, type="text", debounce=True, style={'display': 'inline-block'})
                ], style={'display': 'inline-block'}),
                html.Div(id = {"type":'second-filter-container', "index":idx}, children=[
                    html.Button('Add OR filter', id = {"type":'add-or-filter', "index":idx}, n_clicks=0),
                ], style={'display': 'inline-block', 'margin-left':'15px'})
            ])

    return new_filter

def new_empty_second_filter(idx, labels):
    new_filter = [
        html.Div('OR',style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
        dcc.Dropdown(id={"type":'second-filter-dropdown', "index":idx}, options=labels, style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px', 'width':'200px'}),
        dcc.Dropdown(id={"type":'second-filter-operator', "index":idx}, options=['<','<=','=','!=','=>','>'], value = '<=', style={'display': 'inline-block', 'margin-left':'5px', 'margin-right':'5px', 'width':'40px'}),
        dcc.Input(id={"type":'second-filter-value', "index":idx}, type="text", debounce=True, value=0, style={'display': 'inline-block'})
    ]

    return new_filter