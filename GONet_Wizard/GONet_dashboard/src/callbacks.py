from dash.dependencies import Input, Output, State
from .server import app
import os, json, datetime
from . import env
from . import utils
from dash import no_update, ctx
import numpy as np
from dash import html
from GONet_utils import GONetFile

#upload image and storing the data.
@app.callback(
    Output('data-json', 'data'),
    Output('labels', 'data'),
    Output("x-axis-dropdown",'options'),
    Output("y-axis-dropdown",'options'),
    #---------------------
    Input("dummy",'children')
)
def load(_):
    utils.debug()

    data = {'night':[], 'idx':[], 'channel':[]}
    labels = {}

    image_idx = -1

    for n,night in enumerate(sorted(os.listdir(env.ROOT))):
        if not os.path.isdir(env.ROOT+night): continue
        json_file = env.ROOT+night+f'/{night}_nn.json'
        if not os.path.isfile(json_file): continue
        with open(json_file) as inp:
            night_dict = json.load(inp)
            if len(data['night'])==0:
                labels['gen'] = [l for l in night_dict[0] if l not in env.CHANNELS]
                labels['gen'] = labels['gen'] + ['blue-green', 'green-red', 'blue-red']
                data={**data, **{l:[] for l in labels['gen']}}
                labels['fit'] = [l for l in night_dict[0]['red']]
                data={**data, **{l:[] for l in labels['fit']}}
            for img in night_dict:
                image_idx += 1
                for c in env.CHANNELS:
                    data['night'].append(night)
                    data['idx'].append(image_idx)
                    data['channel'].append(c)
                    data['blue-green'].append(img['blue']['mean']/img['green']['mean'])
                    data['green-red'].append(img['green']['mean']/img['red']['mean'])
                    data['blue-red'].append(img['blue']['mean']/img['red']['mean'])
                    for label in labels['gen']:
                        if label not in img:continue
                        if label == "date":
                            data[label].append(datetime.datetime.fromisoformat(img[label]).astimezone(env.LOCAL_TZ))
                        else:
                            data[label].append(img[label])
                    for label in labels['fit']:
                        data[label].append(img[c][label])

    labels_dropdown = [{"label": l, "value": l} for l in labels['gen'] if l != 'filename']
    labels_dropdown = labels_dropdown + [{"label": l, "value": l} for l in labels['fit']]

    return data, labels, labels_dropdown, labels_dropdown


@app.callback(
    Output("main-plot",'figure', allow_duplicate=True),
    #---------------------
    Input("x-axis-dropdown",'value'),
    Input("y-axis-dropdown",'value'),
    Input("switch", 'data'),
    Input("filters",'value'),
    Input("show-filtered-data-switch", 'on'),
    Input("fold-time-switch",'on'),
    #---------------------
    State("main-plot",'figure'),
    State("data-json",'data'),
    State("labels",'data'),
    State("big-points",'data'),
    State("sun-switch", 'on'),
    State("moon-switch", 'on'),
    State("condition-code-switch", 'on'),
    State("sun-altitude",'value'),
    State("moon-altitude",'value'),
    State("moon-illumination",'value'),
    State("condition-code",'value'),
    prevent_initial_call=True
)
def plot(x_label, y_label, _, filters, show_filtered_points, fold_switch, fig, all_data, labels, big_point_idx, sun_switch, moon_switch, coco_switch, sun_altitude, moon_altitude, moon_illumination, coco):
    utils.debug()

    if x_label is None or y_label is None:
        return no_update

    if fig is not None:
        # Showing/hiding filtered data
        if ctx.triggered_id == 'show-filtered-data-switch':
            if len([img for img in fig['data'] if img['filtered']])==0:
                return no_update
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
                            

            return utils.sort_figure(fig)

        # Showing/hiding filtered data
        if ctx.triggered_id == 'filters':
            if x_label in labels['gen'] and y_label in labels['gen']:
                return no_update
            # Showing filtered data
            for to_be_plotted_f in filters:
                if to_be_plotted_f not in set([img['channel'] for img in fig['data']]):
                    fig = utils.plot_scatter(x_label, y_label, sun_altitude, moon_altitude, moon_illumination, coco, all_data, labels, [to_be_plotted_f], fig, show_filtered_points, fold_switch)
                    if big_point_idx is not None:
                        fig = utils.plot_big_points(all_data, big_point_idx, x_label, y_label, fig, fold_switch)
                    return utils.sort_figure(fig)
            # Hiding filtered data
            for i,img in reversed(list(enumerate(fig['data']))):
                if img['channel'] not in filters:
                    fig['data'].pop(i)
                return utils.sort_figure(fig)
        
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

    if ctx.triggered_id in ['switch']:
        try:
            fig['layout']['xaxis']['range'] = xaxis_range[:]
            fig['layout']['yaxis']['range'] = yaxis_range[:]
        except:
            pass

    if sun_switch:
        sun_altitude = float(sun_altitude)
    else:
        sun_altitude = None

    if moon_switch:
        moon_altitude = float(moon_altitude)
        moon_illumination = float(moon_illumination)
    else:
        moon_altitude = None
        moon_illumination = None

    if coco_switch:
        coco = int(coco)
    else:
        coco = None
    fig = utils.plot_scatter(x_label, y_label, sun_altitude, moon_altitude, moon_illumination, coco, all_data, labels, filters, fig, show_filtered_points, fold_switch)

    if big_point_idx is not None:
        fig = utils.plot_big_points(all_data, big_point_idx, x_label, y_label, fig, fold_switch)

    return fig
        

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
    State("x-axis-dropdown",'value'),
    State("y-axis-dropdown",'value'),
    State("fold-time-switch",'on'),
    prevent_initial_call=True
)
def info(clickdata, fig, data, x_label, y_label, fold_switch):
    utils.debug()
    plot_index = clickdata['points'][0]['curveNumber']
    idx = fig['data'][plot_index]['idx'][clickdata['points'][0]['pointIndex']]
    original_channel = fig['data'][plot_index]['channel']
    if original_channel == 'gen':
        original_channel = 'green'
    points = np.array(data['idx']) == idx
    real_idx = np.argmax([np.logical_and(points, np.array(data['channel']) == original_channel)])
    
    # Plotting big point
    fig = utils.plot_big_points(data, real_idx, x_label, y_label, fig, fold_switch)

    # Info table
    table = [html.Tr([html.Td(el),html.Td(data[el][real_idx])]) for el in data]

    # Getting file name of image to show
    night = data['night'][real_idx]
    filename = data['filename'][real_idx]

    filename = env.ROOT_EXT + night + '/Horizontal/' + filename

    go = GONetFile.from_file(filename)
    outfig = {'data':[{'z':getattr(go,original_channel), 'type': 'heatmap'}]}
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
    Output("sun-altitude",'value'),
    Output("switch", 'data', allow_duplicate=True),
    #---------------------
    Input("sun-switch", 'on'),
    Input("sun-altitude",'value'),
    #---------------------
    State("sun-altitude",'placeholder'),
    #---------------------
    prevent_initial_call=True
)
def set_sun_defaults(switch, value, placeholder):
    utils.debug()
    if switch:
        if value is None:
            return placeholder, True
        else:
            return value, True
    else:
        return no_update, False


@app.callback(
    Output("moon-altitude",'value'),
    Output("moon-illumination",'value'),
    Output("switch", 'data', allow_duplicate=True),
    #---------------------
    Input("moon-switch", 'on'),
    Input("moon-altitude",'value'),
    Input("moon-illumination",'value'),
    #---------------------
    State("moon-altitude",'placeholder'),
    State("moon-illumination",'placeholder'),
    #---------------------
    prevent_initial_call=True
)
def set_moon_defaults(switch, value1, value2, placeholder1, placeholder2):
    utils.debug()
    if switch:
        if value1 is None or value2 is None:
            return placeholder1, placeholder2, True
        else:
            return value1, value2, True
    else:
        return no_update, no_update, False


@app.callback(
    Output("condition-code",'value'),
    Output("switch", 'data'),
    #---------------------
    Input("condition-code-switch", 'on'),
    Input("condition-code", 'value'),
    #---------------------
    State("condition-code",'placeholder'),
    #---------------------
    prevent_initial_call=True
)
def change_coco(switch, value, placeholder):
    utils.debug()
    if switch:
        if value is None:
            return placeholder, True
        else:
            return value, True
    else:
        return no_update, False
    
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