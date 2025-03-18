import inspect, datetime
import numpy as np
from GONet_Wizard.GONet_dashboard.src import env
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

    # Retrieving the quantities I am currently plotting
    labels = get_labels(fig)

    # For every GONet image, all_data contains a 3 rows, one for every channel
    # Here I identify what channels I am plotting, and I create a mask isolating
    # the elements in all_data corresponding to those channels.
    channel_filter = {}
    if labels['x'] in env.LABELS['gen'] and labels['y'] in env.LABELS['gen']:
        # If the labels are not channel-specific, the row of any channel can be used
        channel_filter['gen'] = np.array(all_data['channel']) == 'red'
    else:
        for c in channels:
            channel_filter[c] = np.array(all_data['channel']) == c
    
    # The filters array will have a list of masks, one for every active filter
    # Each mask will have len equal to the full all_data database, i.e. the
    # len of any of each column, for instance all_data['channel'].
    filters = []
    for f in active_filters:
        # I will take care of selection filters later
        if f['label'].split()[0]=='Selection':
            primary_filter = np.isin(all_data['idx'],f['value'])
            primary_filter = np.logical_and(primary_filter, channel_filter[c])
            if f['operator'] == 'out':
                primary_filter = ~primary_filter
            filters.append(primary_filter)
    
        else:
            primary_filter = op[f['operator']](np.array(all_data[f['label']]),type(all_data[f['label']][0])(f['value']))

            if 'secondary' in f:
                secondary_filter = op[f['secondary']['operator']](np.array(all_data[f['secondary']['label']]),type(all_data[f['secondary']['label']][0])(f['secondary']['value']))
            else:
                # If there is no secondary filter, I just create an array with all True values
                secondary_filter = np.full(len(all_data['channel']), False)
            filters.append(np.logical_or(primary_filter, secondary_filter))

        # if f['label'].split()[0]=='Selection':
    #             np.full(len(all_data['channel']), True)  # Initialize with all False
    #             mask[fig['data'][0]['idx'][f['value']]] = True
    #             filters.append(mask)
    #         else:

    # I recursively apply all the masks in filters, starting from an array with all True values
    total_filter = np.full(len(all_data['channel']), True)
    for f in filters:
        total_filter = np.logical_and(total_filter,f)

    # copying the columns we are interested in, plus the index column
    # to 3 more generic x_data, y_data, real_idx arrays, and making 
    # them numpy arrays. Also taking care of any folding needed
    # if we want to visualize the night evolution rather than
    # the whole time evolution.
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
    y_data = np.array(all_data[labels['y']])
    real_idx = np.array(all_data['idx'])


    for c in channel_filter:
        marker = {
                'color': env.COLORS[c](1),
                'symbol': 'circle'
            }
        filtered_out_marker = {
                        'color': env.COLORS[c](0.2) if show_filtered_points else env.COLORS[c](0),
                        'symbol': 'circle'
                    }
        selected_data_filter = np.logical_and(total_filter, channel_filter[c])
        fig['data'].append({
            'hovertemplate': labels['x']+'=%{x}<br>'+labels['y']+'=%{y}',
            'x': x_data[selected_data_filter],
            'y': y_data[selected_data_filter],
            'type': 'scatter',
            'mode': 'markers',
            'marker': marker,
            'unselected': {'marker': marker},
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
                'marker': filtered_out_marker,
                'unselected': {'marker': filtered_out_marker},
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

        marker_big_point = {
                'color': img['marker']['color'],
                'symbol': 'circle',
                'size': 15,
                'line':{
                    'width':0 if img['hidden'] else 2,
                    'color':'DarkSlateGrey'
                }
            }

        big_point_figs.append({
            'x': x_data,
            'y': y_data,
            'type': 'scatter',
            'mode': 'markers',
            'marker': marker_big_point,
            'unselected': {'marker': marker_big_point},
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

def new_selection_filter(idx, selected_indexes):

    new_filter = html.Div(id = {"type":'filter-container', "index":idx}, children=[
                html.Div(id = {"type":'first-filter-container', "index":idx}, children=[
                    daq.BooleanSwitch(id={"type":'filter-switch', "index":idx}, on=False, style={'display': 'inline-block'}),
                    dcc.Dropdown(id={"type":'filter-dropdown', "index":idx}, options=[f'Selection {idx}'], value=f'Selection {idx}',style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px', 'width':'200px'}),
                    dcc.Store(id={"type":'filter-selection-data', "index": idx}, data = selected_indexes),
                    dcc.Dropdown(id={"type":'filter-operator', "index":idx}, options=['in', 'out'], value = 'in', style={'display': 'inline-block', 'margin-left':'5px', 'margin-right':'5px', 'width':'40px'}),
                ])
            ])

    return new_filter