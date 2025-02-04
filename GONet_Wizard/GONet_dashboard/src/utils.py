import inspect, datetime
import numpy as np
from . import env
import operator

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


def plot_scatter(x_label, y_label, all_data, labels, channels, fig, active_filters, show_filtered_points, fold_switch):
    channel_filter = {}
    if x_label in labels['gen'] and y_label in labels['gen']:
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
    # if moon_altitude is not None:
    #     filters.append(np.logical_or(np.array(all_data["moonaltaz"]) <= float(moon_altitude), np.array(all_data["moon_illumination"]) <= float(moon_illumination)))

    total_filter = np.full(len(all_data['channel']), True)
    for f in filters:
        total_filter = np.logical_and(total_filter,f)

    if x_label == 'date' and fold_switch:
        time = []
        for t in all_data[x_label]:
            if datetime.datetime.fromisoformat(t).time()>env.DAY_START:
                time.append('2025-01-01T'+t.split('T')[1])
            else:
                time.append('2025-01-02T'+t.split('T')[1])
        x_data = np.array(time)
    else:
        x_data = np.array(all_data[x_label])
    y_data = np.array(all_data[y_label])
    real_idx = np.array(all_data['idx'])

    for c in channel_filter:
        selected_data_filter = np.logical_and(total_filter, channel_filter[c])
        fig['data'].append({
            'hovertemplate': x_label+'=%{x}<br>'+y_label+'=%{y}',
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
                'hovertemplate': x_label+'=%{x}<br>'+y_label+'=%{y}',
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

def plot_big_points(data, idx_big_point, x_label, y_label, fig, fold_switch):

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

        x_data = np.array(data[x_label])[selected_data_filter]
        y_data = np.array(data[y_label])[selected_data_filter]

        if x_label == 'date' and fold_switch:
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
            'filtered': img['filtered'],
            'hidden':img['hidden'],
            'big_point': True
        })

    fig['data'] = fig['data'] + big_point_figs

    return fig

