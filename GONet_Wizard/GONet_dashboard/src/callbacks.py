from dash.dependencies import Input, Output, State, ALL, MATCH
from .server import app
import os, json, datetime
from . import env
from . import utils
from dash import no_update, ctx, dcc, html
import numpy as np
from GONet_utils import GONetFile
import dash_daq as daq

#upload image and storing the data.
@app.callback(
    Output('data-json', 'data'),
    Output("x-axis-dropdown",'options'),
    Output("y-axis-dropdown",'options'),
    #---------------------
    Input("load-data",'n_clicks')
)
def load(_):
    utils.debug()

    data = {'night':[], 'idx':[], 'channel':[]}

    image_idx = -1

    for n,night in enumerate(sorted(os.listdir(env.ROOT))):
        if not os.path.isdir(env.ROOT+night): continue
        json_file = env.ROOT+night+f'/{night}_nn.json'
        if not os.path.isfile(json_file): continue
        with open(json_file) as inp:
            night_dict = json.load(inp)
            if len(data['night'])==0:
                env.LABELS['gen'] = [l for l in night_dict[0] if l not in env.CHANNELS]
                env.LABELS['gen'] = env.LABELS['gen'] + ['blue-green', 'green-red', 'blue-red']
                data={**data, **{l:[] for l in env.LABELS['gen']}}
                env.LABELS['fit'] = [l for l in night_dict[0]['red']]
                data={**data, **{l:[] for l in env.LABELS['fit']}}
            for img in night_dict:
                image_idx += 1
                for c in env.CHANNELS:
                    data['night'].append(night)
                    data['idx'].append(image_idx)
                    data['channel'].append(c)
                    data['blue-green'].append(img['blue']['mean']/img['green']['mean'])
                    data['green-red'].append(img['green']['mean']/img['red']['mean'])
                    data['blue-red'].append(img['blue']['mean']/img['red']['mean'])
                    for label in env.LABELS['gen']:
                        if label not in img:continue
                        if label == "date":
                            data[label].append(datetime.datetime.fromisoformat(img[label]).astimezone(env.LOCAL_TZ))
                        else:
                            data[label].append(img[label])
                    for label in env.LABELS['fit']:
                        data[label].append(img[c][label])

    labels_dropdown = [{"label": l, "value": l} for l in env.LABELS['gen'] if l != 'filename']
    labels_dropdown = labels_dropdown + [{"label": l, "value": l} for l in env.LABELS['fit']]

    return data, labels_dropdown, labels_dropdown


@app.callback(
    Output("main-plot",'figure', allow_duplicate=True),
    Output("stats-table", 'children'),
    #---------------------
    Input("x-axis-dropdown",'value'),
    Input("y-axis-dropdown",'value'),
    Input("active-filters",'data'),
    Input("channels",'value'),
    Input("show-filtered-data-switch", 'on'),
    Input("fold-time-switch",'on'),
    #---------------------
    State("main-plot",'figure'),
    State("data-json",'data'),
    State("big-points",'data'),
    prevent_initial_call=True
)
def plot(x_label, y_label, active_filters, channels, show_filtered_points, fold_switch, fig, all_data, big_point_idx):
    utils.debug()

    if x_label is None or y_label is None:
        return no_update, no_update

    if fig is not None:
        # Showing/hiding filtered data
        if ctx.triggered_id == 'show-filtered-data-switch':
            if len([img for img in fig['data'] if img['filtered']])==0:
                return no_update, no_update
            # Showing
            if show_filtered_points:
                for i,img in reversed(list(enumerate(fig['data']))):
                    if img['filtered']:
                        fig['data'][i]['marker']['color'] = "rgba(" + ','.join(fig['data'][i]['marker']['color'][5:-1].split(',')[:-1]) + ",0.2)"
                        fig['data'][i]['hoverinfo'] = "x+y+text+channel"
                        fig['data'][i]['hovertemplate'] = x_label+'=%{x}<br>'+y_label+'=%{y}'
                        fig['data'][i]['hidden'] = False
                        if 'line' in fig['data'][i]['marker']:
                            fig['data'][i]['marker']['line']['width']=2
            # Hiding
            else:
                for i,img in reversed(list(enumerate(fig['data']))):
                    if img['filtered']:
                        fig['data'][i]['marker']['color'] = "rgba(" + ','.join(fig['data'][i]['marker']['color'][5:-1].split(',')[:-1]) + ",0)"
                        fig['data'][i]['hoverinfo'] = "none"
                        fig['data'][i]['hovertemplate'] = None
                        fig['data'][i]['hidden'] = True
                        if 'line' in fig['data'][i]['marker']:
                            fig['data'][i]['marker']['line']['width']=0
                            

            return utils.sort_figure(fig), no_update

        # Adding/removing channel data
        if ctx.triggered_id == 'channels':
            if x_label in env.LABELS['gen'] and y_label in env.LABELS['gen']:
                return no_update, no_update
            # Adding channel
            for to_be_plotted_f in channels:
                if to_be_plotted_f not in set([img['channel'] for img in fig['data']]):
                    fig = utils.plot_scatter(all_data, [to_be_plotted_f], fig, active_filters, show_filtered_points, fold_switch)
                    if big_point_idx is not None:
                        fig = utils.plot_big_points(all_data, big_point_idx, fig, fold_switch)
                    return utils.sort_figure(fig), utils.get_stats(fig)
            # Removing channel
            for i,img in reversed(list(enumerate(fig['data']))):
                if img['channel'] not in channels:
                    fig['data'].pop(i)
                return utils.sort_figure(fig), utils.get_stats(fig)
        
        # If I get here, it means that a figure exists, but I'm probably activating or deactivating a filter
        # So let's keep the axis ranges

        if 'range' in fig['layout']['xaxis']:
            xaxis_range = fig['layout']['xaxis']['range']
            yaxis_range = fig['layout']['yaxis']['range']
        

    fig = {
        'data': [],
        'layout': {
            'xaxis': {'title': {'text': x_label}},
            'yaxis': {'title': {'text': y_label}}
        }
    }

    if ctx.triggered_id in ['active-filters']:
        try:
            fig['layout']['xaxis']['range'] = xaxis_range[:]
            fig['layout']['yaxis']['range'] = yaxis_range[:]
        except:
            pass

    fig = utils.plot_scatter(all_data, channels, fig, active_filters, show_filtered_points, fold_switch)

    if big_point_idx is not None:
        fig = utils.plot_big_points(all_data, big_point_idx, fig, fold_switch)

    return fig, utils.get_stats(fig)
        

@app.callback(
    Output("gonet-image",'figure'),
    Output("main-plot",'figure', allow_duplicate=True),
    Output("info-table",'children'),
    Output("big-points",'data'),
    #---------------------
    Input("main-plot",'clickData'),
    #---------------------
    State("main-plot",'figure'),
    State("data-json",'data'),
    State("fold-time-switch",'on'),
    #---------------------
    prevent_initial_call=True
)
def info(clickdata, fig, data, fold_switch):
    utils.debug()
    plot_index = clickdata['points'][0]['curveNumber']
    idx = fig['data'][plot_index]['idx'][clickdata['points'][0]['pointIndex']]
    original_channel = fig['data'][plot_index]['channel']
    if original_channel == 'gen':
        original_channel = 'green'
    points = np.array(data['idx']) == idx
    real_idx = np.argmax([np.logical_and(points, np.array(data['channel']) == original_channel)])
    
    # Plotting big point
    fig = utils.plot_big_points(data, real_idx, fig, fold_switch)

    # Info table
    table = [html.Tr([html.Td(el),html.Td(data[el][real_idx])]) for el in data]

    # Getting file name of image to show
    night = data['night'][real_idx]
    filename = data['filename'][real_idx]

    filename = env.ROOT_EXT + night + '/Horizontal/' + filename

    go = GONetFile.from_file(filename)
    outfig = {'data':[{'z':getattr(go,original_channel), 'type': 'heatmap'}], 'layout':{'showlegend': False}}
    del go

    # Overplotting extraction region
    # Center
    outfig['data'].append({'x': [data['center_x'][real_idx]], 'y': [data['center_y'][real_idx]], 'type': 'scatter', 'mode': 'markers', 'marker': {'color':'rgba(0, 0, 0, 1)', 'symbol': 'circle'}})

    #Circle
    c_x, c_y = [],[]
    for ang in np.linspace(0,2*np.pi,25):
        c_x.append(data['center_x'][real_idx]+data['extraction_radius'][real_idx]*np.cos(ang))
        c_y.append(data['center_y'][real_idx]+data['extraction_radius'][real_idx]*np.sin(ang))

    outfig['data'].append({'x': c_x, 'y': c_y, 'type': 'scatter', 'mode': 'lines', 'marker': {'color':'rgba(0, 0, 0, 1)', 'symbol': 'circle'}})

    return outfig, fig, table, real_idx

    
@app.callback(
    Output("fold-time-switch",'disabled'),
    Output("fold-time-switch",'on'),
    #---------------------
    Input("x-axis-dropdown",'value'),
    #---------------------
    prevent_initial_call=True
)
def activate_fold_switch(x_label):
    utils.debug()

    if x_label == 'date':
        return False, False
    else:
        return True, False
    

@app.callback(
    Output("custom-filter-container",'children'),
    #---------------------
    Input("add-filter",'n_clicks'),
    #---------------------
    State("custom-filter-container",'children'),
    State("x-axis-dropdown",'options'),
    #---------------------
    prevent_initial_call=True
)
def add_filter(_, filter_div, labels):
    utils.debug()

    n_filter = len(filter_div)

    new_filter = html.Div(id = {"type":'filter-container', "index":n_filter}, children=[
                html.Div(id = {"type":'first-filter-container', "index":n_filter}, children=[
                    daq.BooleanSwitch(id={"type":'filter-switch', "index":n_filter}, on=False, style={'display': 'inline-block'}),
                    dcc.Dropdown(id={"type":'filter-dropdown', "index":n_filter}, options=labels, style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px', 'width':'200px'}),
                    dcc.Dropdown(id={"type":'filter-operator', "index":n_filter}, options=['<','<=','=','!=','=>','>'], value = '<=', style={'display': 'inline-block', 'margin-left':'5px', 'margin-right':'5px', 'width':'40px'}),
                    dcc.Input(id={"type":'filter-value', "index":n_filter}, type="text", debounce=True, style={'display': 'inline-block'})
                ], style={'display': 'inline-block'}),
                html.Div(id = {"type":'second-filter-container', "index":n_filter}, children=[
                    html.Button('Add OR filter', id = {"type":'add-or-filter', "index":n_filter}, n_clicks=0),
                ], style={'display': 'inline-block', 'margin-left':'15px'})
            ])

    filter_div.append(new_filter)
    return filter_div

@app.callback(
    Output({"type": "second-filter-container", "index": MATCH}, 'children'),
    #---------------------
    Input({"type": "add-or-filter", "index": MATCH}, 'n_clicks'),
    #---------------------
    State({"type": "add-or-filter", "index": MATCH}, 'id'),
    State("x-axis-dropdown",'options'),
    #---------------------
    prevent_initial_call=True
)
def add_or_filter(_, id, labels):
    utils.debug()
    
    idx = id['index']

    new_filter = [
        html.Div('OR',style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px',}),
        dcc.Dropdown(id={"type":'second-filter-dropdown', "index":idx}, options=labels, style={'display': 'inline-block', 'margin-left':'15px', 'margin-right':'15px', 'width':'200px'}),
        dcc.Dropdown(id={"type":'second-filter-operator', "index":idx}, options=['<','<=','=','!=','=>','>'], value = '<=', style={'display': 'inline-block', 'margin-left':'5px', 'margin-right':'5px', 'width':'40px'}),
        dcc.Input(id={"type":'second-filter-value', "index":idx}, type="text", debounce=True, value=0, style={'display': 'inline-block'})
    ]

    return new_filter


@app.callback(
    Output({"type": "filter-value", "index": MATCH}, 'value'),
    #---------------------
    Input({"type": "filter-dropdown", "index": MATCH}, 'value'),
    #---------------------
    prevent_initial_call=True
)
def update_main_filters_label(label):
    utils.debug()
    
    if label in env.DEFAULT_FILTER_VALUES:
        return env.DEFAULT_FILTER_VALUES[label]
    else:
        return None

@app.callback(
    Output({"type": "second-filter-value", "index": MATCH}, 'value'),
    #---------------------
    Input({"type": "second-filter-dropdown", "index": MATCH}, 'value'),
    #---------------------
    prevent_initial_call=True
)
def update_secondary_filters_label(label):
    utils.debug()
    
    if label in env.DEFAULT_FILTER_VALUES:
        return env.DEFAULT_FILTER_VALUES[label]
    else:
        return None
    

@app.callback(
    Output("active-filters",'data'),
    #---------------------
    Input({"type": "filter-switch", "index": ALL}, 'on'),
    Input({"type": "filter-operator", "index": ALL}, 'value'),
    Input({"type": "filter-value", "index": ALL}, 'value'),
    Input({"type": "second-filter-operator", "index": ALL}, 'value'),
    Input({"type": "second-filter-value", "index": ALL}, 'value'),
    #---------------------
    State({"type": "filter-dropdown", "index": ALL}, 'value'),
    State({"type": "second-filter-dropdown", "index": ALL}, 'value'),
    State({"type": "second-filter-value", "index": ALL}, 'id'),
    State("active-filters",'data'),
    #---------------------
    prevent_initial_call=True
)
def update_filters(switches, ops, values, second_ops, second_values, labels, second_labels, second_ids, filters_before):
    utils.debug()

    active_filters=[]

    for i,s in enumerate(switches):
        if s and labels[i] is not None and values[i] is not None:
            active_filters.append({'label': labels[i], 'operator': ops[i], 'value': values[i]})
            for j,id in enumerate(second_ids):
                if id['index'] == i and second_labels[j] is not None and second_values[j] is not None:
                    active_filters[-1]['secondary'] = {'label': second_labels[j], 'operator': second_ops[j], 'value': second_values[j]}


    if filters_before != active_filters:
        return active_filters
    else:
        return no_update

@app.callback(
    Output("download-json", 'data'),
    #---------------------
    Input("export-data", 'n_clicks'),
    #---------------------
    State("main-plot",'figure'),
    State("data-json",'data'),
    # State("channels",'value'),
    #---------------------
    prevent_initial_call=True
)
def export_data(_, fig, data):#, channels):
    utils.debug()

    json_out = []

    # The indexes will be the same for all the channels
    # So I take the indexes from only one of them
    idx_list = [img['idx'] for img in fig['data'] if not img['filtered'] and not img['big_point']][0]

    # Converting the list into a numpy array only once here so that I can
    # use np.where later multiple times
    data_idx = np.array(data['idx'])
    data_channel = np.array(data['channel'])

    for i in idx_list:
        out_dict = {}
        # `data` will have 3 entries with the same idx (one per channel)
        # so `matching_idx` will be a list of 3 elements.
        # Taking just the first to fetch the labels unrelated to the channel
        matching_idx = np.argwhere(data_idx == i)[0][0]

        for label in ['filename','night'] + env.LABELS['gen']:
            if label == 'idx': continue
            out_dict[label] = data[label][matching_idx]
        
        for c in env.CHANNELS:
            out_dict[c]={}
            matching_idx_and_channel = np.argwhere((data_idx == i) & (data_channel==c))[0][0]
            for label in env.LABELS['fit']:
                out_dict[c][label] = data[label][matching_idx_and_channel]

        json_out.append(out_dict)

    return dict(content=json.dumps(json_out, indent=4), filename="filtered_data.json")