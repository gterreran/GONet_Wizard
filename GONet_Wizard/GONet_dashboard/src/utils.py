"""
GONet Wizard Utility Functions.

This module provides reusable functions for plotting, filtering, statistical analysis,
and layout generation within the GONet Wizard dashboard application. These functions
support the construction of `Dash <https://dash.plotly.com/>`_ figures, dynamic filter UI elements, and filter logic
used in the callback system.

`Dash <https://dash.plotly.com/>`_ components from `dash` and `dash_daq` are used to construct UI elements dynamically.

**Globals**

- ``op`` :class:`dict` : Dictionary mapping string operators (e.g., '<', '!=') to their Python equivalents.

**Functions**

- :func:`debug` : debugging. 
- :func:`sort_figure` : Reorders the traces in a Plotly figure based on filtering and highlight status.
- :func:`get_labels` : Extracts the axis label text from a Plotly figure layout.
- :func:`plot_scatter` : Update a Plotly figure by adding scatter traces for selected and filtered data.
- :func:`plot_big_points` : Highlight a selected point in the scatter plot by adding enlarged "big point" markers.
- :func:`get_stats` : Compute summary statistics (mean and standard deviation) for plotted x and y values.
- :func:`new_empty_filter` : Create a `Dash <https://dash.plotly.com/>`_ component representing an empty primary filter block.
- :func:`new_empty_second_filter` : Create a `Dash <https://dash.plotly.com/>`_ component block representing a secondary (OR) filter.
- :func:`new_selection_filter` : Create a `Dash <https://dash.plotly.com/>`_ component for a selection-based filter using manually selected points.

"""
import inspect, datetime
import numpy as np
from GONet_Wizard.GONet_dashboard.src import env
import operator
from dash import html, dcc
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
    This is just for debugging purposes.
    It prints the function in which it is called,
    and the line at which it is called.
    '''

    print(
        '{} fired. Line {}.'.format(
            inspect.stack()[1][3],
            inspect.stack()[1][2]))

def sort_figure(fig: dict) -> dict:
    """
    Reorders the traces in a Plotly figure based on filtering and highlight status.

    This function reorders the entries in the ``fig['data']`` list so that:

    1. Filtered points (not highlighted) are drawn first.
    2. Unfiltered points are drawn next (these should be visually dominant).
    3. Highlighted "big points" are drawn last so they appear on top.

    Parameters
    ----------
    fig : :class:`dict`
        A Plotly figure dictionary with a "data" key containing traces.
        Each trace is expected to include boolean keys: "filtered" and "big_point".

    Returns
    -------
    :class:`dict`
        The modified Plotly figure with reordered data traces.
    """
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

def get_labels(fig: dict) -> dict:
    """
    Extracts the axis label text from a Plotly figure layout.

    This function retrieves the `xaxis` and `yaxis` title strings from the figure's layout
    and returns them as a dictionary keyed by `'x'` and `'y'`.

    Parameters
    ----------
    fig : :class:`dict`
        A Plotly figure dictionary expected to have keys: `'layout' → 'xaxis'/'yaxis' → 'title' → 'text'`.

    Returns
    -------
    :class:`dict`
        A dictionary with keys `'x'` and `'y'`, mapping to the corresponding axis labels as strings.
    """
    return {'x': fig['layout']['xaxis']['title']['text'], 'y': fig['layout']['yaxis']['title']['text']}

def plot_scatter(
    all_data: dict,
    channels: list,
    fig: dict,
    active_filters: list,
    show_filtered_points: bool,
    fold_switch: bool
) -> dict:
    """
    Update a Plotly figure by adding scatter traces for selected and filtered data.

    This function builds the main scatter plot based on selected channels, applied filters,
    and folding settings. It appends new traces to the input figure dictionary for both
    visible (selected) and hidden (filtered out) data points.

    Parameters
    ----------
    all_data : :class:`dict`
        The full data dictionary containing all measured quantities. Each key corresponds
        to a column, with values as lists of entries (e.g., 'idx', 'channel', 'date', etc.).
    channels : :class:`list`
        A list of channel names (e.g., ['red', 'green', 'blue']) to include in the plot.
    fig : :class:`dict`
        A Plotly figure dictionary that will be modified in-place by appending scatter traces.
    active_filters : :class:`list`
        A list of active filters, each represented as a dictionary with keys like 'label',
        'operator', 'value', and optionally 'secondary'.
    show_filtered_points : :class:`bool`
        Whether to display the filtered-out points in the plot (with lower opacity).
    fold_switch : :class:`bool`
        Whether to fold time-based x-axis values into a 24-hour night-based view.

    Returns
    -------
    :class:`dict`
        The modified Plotly figure with updated 'data' containing scatter traces for each channel.
    """

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

def plot_big_points(data: dict, idx_big_point: int, fig: dict, fold_switch: bool) -> dict:
    """
    Highlight a selected point in the scatter plot by adding enlarged "big point" markers.

    This function removes any previously plotted big points and appends new, enlarged markers
    corresponding to the selected index. It supports time-folding if the x-axis is temporal.

    Parameters
    ----------
    data : :class:`dict`
        The full data dictionary containing measurement entries. Each key corresponds to a quantity
        such as 'channel', 'idx', or a plotted axis label.
    idx_big_point : :class:`int`
        Index of the selected point to be highlighted.
    fig : :class:`dict`
        The Plotly figure to be modified. New traces will be appended to its `'data'` field.
    fold_switch : :class:`bool`
        Whether to fold time values to a 24-hour display anchored to the astronomical day.

    Returns
    -------
    :class:`dict`
        The updated Plotly figure dictionary with big point highlights added.
    """

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

def get_stats(fig: dict) -> list:
    """
    Compute summary statistics (mean and standard deviation) for plotted x and y values.

    This function extracts unfiltered, non-highlighted data from the figure and calculates
    per-axis statistics. It builds an HTML table as a list of `Dash <https://dash.plotly.com/>`_ row components to be
    rendered in the dashboard's stats panel.

    Parameters
    ----------
    fig : :class:`dict`
        A Plotly figure dictionary containing the data traces used for plotting.

    Returns
    -------
    :class:`list`
        A list of :class:`dash.html.Tr` elements representing the statistics table rows.
    """

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

    formatted_stats_table = [html.Tr([html.Td(el[val]) for el in stats_table[axis] for val in ['label', 'value']]) for axis in ['x', 'y']]

    return formatted_stats_table


def new_empty_filter(idx: int, labels: list) -> html.Div:
    """
    Create a `Dash <https://dash.plotly.com/>`_ component representing an empty primary filter block.

    This function generates a new UI element for a filter container, including:
    - A toggle switch to activate the filter
    - Dropdowns for selecting the data field and comparison operator
    - An input box for entering the comparison value
    - A button to optionally add a secondary (OR) filter

    Parameters
    ----------
    idx : :class:`int`
        The index of the filter, used to uniquely identify its subcomponents.
    labels : :class:`list`
        A list of dictionaries defining the dropdown options for the filter field selector.

    Returns
    -------
    :class:`dash.html.Div`
        A fully constructed :dashdoc:`Dash Div <dash-html-components/div>` component containing the filter UI.
    """

    new_filter = html.Div(className="custom-filter-container", id = {"type":'custom-filter-container', "index":idx}, children=[
                html.Div(className="first-filter-container", id = {"type":'first-filter-container', "index":idx}, children=[
                    html.Div(className = 'switch-container', id = {"type":'filter-switch-container', "index":idx}, children=
                        daq.BooleanSwitch(className='switch', id={"type":'filter-switch', "index":idx}, on=False),
                    ),
                    dcc.Dropdown(className="custom-filter-dropdown", id={"type":'filter-dropdown', "index":idx}, options=labels),
                    dcc.Dropdown(className="custom-filter-operator", id={"type":'filter-operator', "index":idx}, options=['<','<=','=','!=','=>','>'], value = '<='),
                    dcc.Input(className="custom-filter-value", id={"type":'filter-value', "index":idx}, type="text", debounce=True)
                ]),
                html.Div(className="second-filter-container", id = {"type":'second-filter-container', "index":idx}, children=[
                    html.Button(className="OR-filter-button", children='Add OR filter', id = {"type":'add-or-filter', "index":idx}, n_clicks=0),
                ])
            ])

    return new_filter

def new_empty_second_filter(idx: int, labels: list) -> list:
    """
    Create a `Dash <https://dash.plotly.com/>`_ component block representing a secondary (OR) filter.

    This function returns a list of `Dash <https://dash.plotly.com/>`_ components corresponding to a secondary filter UI.
    It includes a label ("OR"), a dropdown for field selection, a dropdown for the operator,
    and an input field for the value.

    Parameters
    ----------
    idx : :class:`int`
        The index of the parent filter, used to uniquely identify the subcomponents.
    labels : :class:`list`
        A list of dictionaries representing dropdown options for field selection.

    Returns
    -------
    :class:`list`
        A list of `Dash <https://dash.plotly.com/>`_ components to be inserted into a secondary filter container.
    """
    new_filter = [
        html.Div(className='or-div', id= {"type":'or-div', "index":idx}, children='OR'),
        dcc.Dropdown(className="custom-filter-dropdown", id={"type":'second-filter-dropdown', "index":idx}, options=labels),
        dcc.Dropdown(className="custom-filter-operator", id={"type":'second-filter-operator', "index":idx}, options=['<','<=','=','!=','=>','>'], value = '<='),
        dcc.Input(className="custom-filter-value", id={"type":'second-filter-value', "index":idx}, type="text", debounce=True)
    ]

    return new_filter

def new_selection_filter(idx: int, selected_indexes: list) -> html.Div:
    """
    Create a `Dash <https://dash.plotly.com/>`_ component for a selection-based filter using manually selected points.

    This function generates a filter UI tied to a lasso or box selection on the plot.
    It includes a toggle switch, a dropdown preset to the selection label, a hidden
    data store with the selected indices, and a dropdown to choose inclusion or exclusion.

    Parameters
    ----------
    idx : :class:`int`
        The index of the filter, used to generate unique component IDs.
    selected_indexes : :class:`list`
        A list of data indices representing the points included in the selection.

    Returns
    -------
    :class:`dash.html.Div`
        A :dashdoc:`Dash Div <dash-html-components/div>` component containing the selection-based filter UI.
    """

    new_filter = html.Div(className="custom-filter-container", id = {"type":'custom-filter-container', "index":idx}, children=[
                html.Div(className="first-filter-container", id = {"type":'first-filter-container', "index":idx}, children=[
                    html.Div(className = 'switch-container', id = {"type":'filter-switch-container', "index":idx}, children=
                        daq.BooleanSwitch(className='switch', id={"type":'filter-switch', "index":idx}, on=False),
                    ),
                    dcc.Dropdown(className="custom-filter-dropdown", id={"type":'filter-dropdown', "index":idx}, options=[f'Selection {idx}'], value=f'Selection {idx}'),
                    dcc.Store(id={"type":'filter-selection-data', "index": idx}, data = selected_indexes),
                    dcc.Dropdown(className="custom-filter-operator", id={"type":'filter-operator', "index":idx}, options=['in', 'out'], value = 'in'),
                ])
            ])

    return new_filter