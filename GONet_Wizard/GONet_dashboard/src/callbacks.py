"""
Callbacks for the GONet Dashboard.

This module defines all `Dash <https://dash.plotly.com/>`_ callback functions used to power the interactivity
of the GONet Wizard dashboard. These callbacks handle data loading, filter logic,
plot generation, UI synchronization, and exporting/importing dashboard state.

**Functions**

- :func:`load` : Load available data from the configured ROOT directory and prepare dropdown options.
- :func:`plot` : Update the main plot based on the selected axes, filters, and other plot parameters.
- :func:`info` : Update the UI when a data point in the main plot is clicked.
- :func:`activate_fold_switch` : Toggle the availability of the fold-time switch based on the x-axis selection.
- :func:`add_filter` : Add a new empty filter block to the filter container in the UI.
- :func:`add_or_filter` : Add an additional (OR-based) condition to an existing filter block.
- :func:`update_main_filters_value` : Automatically update the value of the main filter when a filter label is selected.
- :func:`update_secondary_filters_value` : Automatically update the value of the secondary (OR) filter when a label is selected.
- :func:`update_filters` : Assemble and update the active filters list based on user-defined filter inputs.
- :func:`export_data` : Export filtered data from the plot to a downloadable JSON file.
- :func:`save_status` : Save the current dashboard state, including axis selections and filter configurations.
- :func:`load_status` : Load a previously saved dashboard state from a base64-encoded JSON file.
- :func:`update_filter_selection_state` : Enable or disable the "Add Selection Filter" button based on current selection in the plot.
- :func:`add_selection_filter` : Create and add a new filter based on the current selection region in the plot.

"""

import json, base64
import numpy as np

from dash import no_update, ctx, html, clientside_callback
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State, ALL, MATCH

from GONet_Wizard.GONet_dashboard.src.server import app
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_dashboard.src import env
from GONet_Wizard.GONet_dashboard.src import utils


@app.callback(
    Output("alert-container", "data-dummy"),  # can be non-existent — Dash ignores it
    Input("alert-container", "className"),
    prevent_initial_call=True
)
def raise_if_error(classname):
    """
    Forces Dash to treat a callback as failed when an error is detected.

    This listens to changes in the `alert-container.className`. If the class
    includes "error", this indicates that a prior callback caught an exception
    and returned an alert with that classification.

    Raising an exception here causes Dash to invalidate the entire chain of
    dependent callbacks, preventing execution based on faulty or incomplete state.

    Parameters
    ----------
    classname : str
        The class name of the alert container, passed as Input.

    Raises
    ------
    Exception
        Generic exception to halt Dash execution flow when 'error' is present.

    Returns
    -------
    Nothing. Always raises or prevents update.
    """
    if isinstance(classname, str) and "error" in classname:
        raise Exception("Previous callback failed — halting update chain.")
    raise PreventUpdate


@app.callback(
    Output('data-json', 'data'),
    Output("x-axis-dropdown",'options'),
    Output("y-axis-dropdown",'options'),
    Output("alert-container", "children"),
    Output("alert-container", "className"),
    Output("alert-container", "style"),
    #---------------------
    Input("top-container",'children')
)
@utils.debug_print
@utils.handle_errors(n_outputs=3)
def load(_):
    """
    Dash callback to initialize the dashboard data store and dropdown options.

    This function is triggered once when the layout is rendered. It delegates the
    actual data-loading logic to :func:`utils.load_data`, which scans the directory
    specified by the ``GONET_ROOT`` environment variable, loads GONet JSON files,
    and returns a flat dictionary of observations along with axis selection options.

    The callback is wrapped in :func:`handle_errors` to display any exceptions in the
    alert container and halt further callback execution if a failure occurs.

    Parameters
    ----------
    _ : Any
        Dummy input triggered by layout initialization; unused.

    Returns
    -------
    data : dict
        Flattened dictionary of GONet metadata and per-channel measurements,
        to be stored in a hidden dcc.Store component.

    options_x : list of dict
        Dropdown options for selecting the x-axis quantity.

    options_y : list of dict
        Dropdown options for selecting the y-axis quantity.

    alert_message : str
        Content for `alert-container.children` (empty on success).

    alert_class : str
        CSS class for `alert-container.className` (empty or "alert-box error").

    alert_style : dict
        Display style for `alert-container.style` (e.g., visible on error).
    """
    return utils.load_data(env)



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
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def plot(x_label, y_label, active_filters, channels, show_filtered_points, fold_switch, fig, all_data, big_point_idx):
    """
    Update the main scatter plot and statistics table based on the selected parameters and filters.

    This callback is the central engine of the dashboard visualization. It handles a variety of triggers, including:

    - A change in selected x/y axis variables
    - The toggling of filters or updates to active filters
    - Enabling or disabling of channels
    - Switching visibility for filtered-out points
    - Activation of time-folding mode

    Depending on what was triggered, this function can:

    - Regenerate the entire figure from scratch (e.g. if the axis or filters changed)
    - Selectively update specific components (e.g. hiding/showing filtered data or toggling channels)
    - Re-insert a highlighted "big point" for a selected observation
    - Preserve axis ranges when appropriate to improve interactivity

    Parameters
    ----------
    x_label : :class:`str`
        Selected label for the x-axis.
    y_label : :class:`str`
        Selected label for the y-axis.
    active_filters : :class:`list` of :class:`dict`
        List of user-defined filters applied to the data.
    channels : :class:`list` of :class:`str`
        Channels selected for visualization (e.g., 'red', 'green', 'blue').
    show_filtered_points : :class:`bool`
        Whether to visually include the points that were filtered out.
    fold_switch : :class:`bool`
        Whether to fold the x-axis time data to display only night-time variation.
    fig : :class:`dict` or :class:`None`
        The current Plotly figure object. May be reused and updated if possible.
    all_data : :class:`dict`
        Dictionary of all GONet data currently loaded into the dashboard.
    big_point_idx : :class:`int` or :class:`None`
        Index of a selected "big point" to highlight on the plot.

    Returns
    -------
    fig : :class:`dict`
        Updated Plotly figure based on the selected parameters and filters.
    stats : :class:`list`
        Table rows representing statistical summaries (mean ± std) of the plotted data.
    """

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
                        fig['data'][i]['showlegend'] = True
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
                        fig['data'][i]['showlegend'] = False
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
            'paper_bgcolor':env.BG_COLOR,
            'plot_bgcolor':env.BG_COLOR,
            'font': {'color':env.TEXT_COLOR},
            'dragmode': 'lasso',
            'margin': {'l':10, 'r':10, 't':10, 'b':10},
            'xaxis':{
                'title': {'text': x_label},
                'automargin':True,
                'ticks':"outside",
                'mirror':True
            },
            'yaxis':{
                'title': {'text': y_label},
                'automargin':True,
                'ticks':"outside",
                'mirror':True
            },
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
@utils.debug_print
def info(clickdata, fig, data, fold_switch):
    """
    Handle click interactions on the main scatter plot and update the UI accordingly.

    When a user clicks on a data point in the main plot, this callback:
    
    - Highlights the selected point with a larger marker ("big point") in the main figure.
    - Loads and displays the corresponding GONet image for that data point in the right panel.
    - Shows a table containing all metadata associated with the clicked data point.
    - Overlays a circle and center marker to visualize the extraction region on the image.

    Parameters
    ----------
    clickdata : :class:`dict`
        Click event data generated from the main Plotly plot. Contains the clicked curve index
        and point index.
    fig : :class:`dict`
        The current Plotly figure object representing the main scatter plot.
    data : :class:`dict`
        The full dataset previously loaded into the dashboard, including metadata and measurements.
    fold_switch : :class:`bool`
        Whether time folding is enabled for the x-axis. Affects formatting of "big point" display.

    Returns
    -------
    outfig : :class:`dict`
        A Plotly heatmap figure showing the raw GONet image associated with the clicked point.
        The figure includes overlays for the extraction region and center.
    fig : :class:`dict`
        Updated main plot figure with the selected point rendered as a "big point".
    table : :class:`list`
        List of :dashdoc:`dash.html.Tr <dash-html-components/tr>` table row elements, each showing a key-value pair of metadata.
    real_idx : :class:`int`
        Index of the clicked observation in the full dataset.
    """

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
    outfig = {
        'data':[{'z':getattr(go,original_channel), 'type': 'heatmap'}],
        'layout':{
            'showlegend': False,
            'paper_bgcolor':env.BG_COLOR,
            'plot_bgcolor':env.BG_COLOR,
            'font': {'color':env.TEXT_COLOR},
            'margin': {'l':10, 'r':10},
            'xaxis':{
                'automargin':True,
                'ticks':"outside",
                'mirror':True
            },
            'yaxis':{
                'automargin':True,
                'ticks':"outside",
                'mirror':True
            },
        }
    }
    del go

    # Overplotting extraction region
    # Center
    outfig['data'].append({'x': [data['center_x'][real_idx]], 'y': [data['center_y'][real_idx]], 'type': 'scatter', 'mode': 'markers', 'marker': {'color':'rgba(0, 0, 0, 1)', 'symbol': 'circle'}})

    # Circle
    c_x, c_y = [],[]
    for ang in np.linspace(0,2*np.pi,25):
        c_x.append(data['center_x'][real_idx]+data['extraction_radius'][real_idx]*np.cos(ang))
        c_y.append(data['center_y'][real_idx]+data['extraction_radius'][real_idx]*np.sin(ang))

    outfig['data'].append({'x': c_x, 'y': c_y, 'type': 'scatter', 'mode': 'lines', 'marker': {'color':'rgba(0, 0, 0, 1)', 'symbol': 'circle'}})

    return outfig, fig, table, real_idx

    
@app.callback(
    Output("fold-time-switch",'disabled'),
    Output("fold-time-switch",'on', allow_duplicate=True),
    #---------------------
    Input("x-axis-dropdown",'value'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def activate_fold_switch(x_label):
    """
    Toggle the availability of the fold-time switch based on the x-axis selection.

    Parameters
    ----------
    x_label : :class:`str`
        Label selected for the x-axis.

    Returns
    -------
    disabled : :class:`bool`
        Whether the switch should be disabled.
    on : :class:`bool`
        State of the switch.
    """

    if x_label == 'date':
        return False, False
    else:
        return True, False
    

@app.callback(
    Output("custom-filter-container",'children', allow_duplicate=True),
    #---------------------
    Input("add-filter",'n_clicks'),
    #---------------------
    State("custom-filter-container",'children'),
    State("x-axis-dropdown",'options'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def add_filter(_, filter_div, labels):
    """
    Add a new empty filter block to the filter container in the UI.

    Parameters
    ----------
    _ : :class:`Any`
        Dummy input from the button click (not used).
    filter_div : :class:`list`
        Current list of filter components in the container.
    labels : :class:`list` of :class:`dict`
        List of label options for dropdowns.

    Returns
    -------
    filter_div : :class:`list`
        Updated list of filter components with one new filter added.
    """
    
    n_filter = len(filter_div)
    new_empty_filter = utils.new_empty_filter(n_filter, labels)
    filter_div.append(new_empty_filter)

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
@utils.debug_print
def add_or_filter(_, id, labels):
    """
    Add an additional (OR-based) condition to an existing filter block.

    Parameters
    ----------
    _ : :class:`Any`
        Dummy input from the OR-button click (not used).
    id : :class:`dict`
        Dictionary containing the index of the filter block to update.
    labels : :class:`list` of :class:`dict`
        List of label options for the dropdowns.

    Returns
    -------
    new_filter : dash component
        A new filter component to be added to the filter block.
    """
    
    idx = id['index']
    new_filter = utils.new_empty_second_filter(idx, labels)

    return new_filter


@app.callback(
    Output({"type": "filter-value", "index": MATCH}, 'value'),
    #---------------------
    Input({"type": "filter-dropdown", "index": MATCH}, 'value'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def update_main_filters_value(label):
    """
    Automatically update the value of the main filter when a filter label is selected.

    Parameters
    ----------
    label : :class:`str`
        The selected label from the main filter dropdown.

    Returns
    -------
    value : :class:`Any` or :class:`None`
        Default value corresponding to the label, or None if not found.
    """
    
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
@utils.debug_print
def update_secondary_filters_value(label):
    """
    Automatically update the value of the secondary (OR) filter when a label is selected.

    Parameters
    ----------
    label : :class:`str`
        The selected label from the secondary filter dropdown.

    Returns
    -------
    value : :class:`Any` or :class:`None`
        Default value corresponding to the label, or None if not found.
    """
    
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
    Input({"type": "filter-selection-data", "index": ALL}, 'data'),
    Input({"type": "second-filter-operator", "index": ALL}, 'value'),
    Input({"type": "second-filter-value", "index": ALL}, 'value'),
    #---------------------
    State({"type": "filter-dropdown", "index": ALL}, 'value'),
    State({"type": "second-filter-dropdown", "index": ALL}, 'value'),
    State({"type": "second-filter-value", "index": ALL}, 'id'),
    State({"type": "filter-selection-data", "index": ALL}, 'id'),
    State("active-filters",'data'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def update_filters(switches, ops, values, selections, second_ops, second_values, labels, second_labels, second_ids, selections_ids, filters_before):
    """
    Assemble and update the active filters list based on user-defined filter inputs.

    This function collects the current state of all active filters, including their
    labels, operators, and values, and constructs a list of active filters. If a
    secondary (OR) filter is present, it is added as a nested dictionary.

    Parameters
    ----------
    switches : :class:`list` of :class:`bool`
        States of the main filter switches indicating whether each filter is active.
    ops : :class:`list` of :class:`str`
        Comparison operators for each main filter (e.g., '>', '<=', '==').
    values : :class:`list`
        Values selected or entered for each main filter.
    selections : :class:`list`
        Lasso or box selection data used to override value-based filters.
    second_ops : :class:`list` of :class:`str`
        Comparison operators for each secondary filter.
    second_values : :class:`list`
        Values selected or entered for each secondary filter.
    labels : :class:`list` of :class:`str`
        Labels (field names) selected for each main filter.
    second_labels : :class:`list` of :class:`str`
        Labels selected for each secondary filter.
    second_ids : :class:`list` of :class:`dict`
        IDs of the secondary filter value fields, containing the filter index.
    selections_ids : :class:`list` of :class:`dict`
        IDs of the selection-based filters, containing the filter index.
    filters_before : :class:`list` of :class:`dict`
        Previously active filters, used to check whether an update is necessary.

    Returns
    -------
    :class:`list` of :class:`dict` or :class:`dash.no_update`
        Updated list of active filters, or `no_update` if unchanged.
    """

    active_filters=[]
    for i,s in enumerate(switches):
        value = None
        for k, id in enumerate(selections_ids):
            if i == id['index']:
                value = selections[k]
                values.insert(i, None)
                break
        if not value:
            value = values[i]
        if s and labels[i] is not None and value is not None:
            active_filters.append({'label': labels[i], 'operator': ops[i], 'value': value})
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
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def export_data(_, fig, data):#, channels):
    """
    Export filtered data from the plot to a downloadable JSON file.

    This function retrieves all points currently visible in the main plot that are not
    filtered or marked as big points. It extracts relevant metadata and fit parameters
    for each unique index across all channels, organizing the data into a structured JSON
    format for export.

    Parameters
    ----------
    _ : :class:`Any`
        Unused placeholder for the n_clicks input from the export button.
    fig : :class:`dict`
        The Plotly figure dictionary containing plotted data and metadata.
    data : :class:`dict`
        The full dataset loaded into the application, including all measurements
        and metadata for each point.

    Returns
    -------
    :class:`dict`
        A dictionary containing:

        - 'content': JSON string representing the filtered and formatted dataset.
        - 'filename': Suggested filename for the download ("filtered_data.json").

    """

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

        for label in ['filename'] + env.LABELS['gen']:
            if label == 'idx': continue
            out_dict[label] = data[label][matching_idx]
        
        for c in env.CHANNELS:
            out_dict[c]={}
            matching_idx_and_channel = np.argwhere((data_idx == i) & (data_channel==c))[0][0]
            for label in env.LABELS['fit']:
                out_dict[c][label] = data[label][matching_idx_and_channel]

        json_out.append(out_dict)

    return dict(content=json.dumps(json_out, indent=4), filename="filtered_data.json")

# ------------------------------------------------------------------------------
# Clientside Callback: Download Dashboard Status as JSON
# ------------------------------------------------------------------------------
#
# This clientside callback enables users to export the current dashboard status
# (e.g., selected axes, filters, and switches) as a downloadable JSON file.
# The data is serialized on the client and offered as a file via the browser’s
# native download mechanism, using a temporary Blob URL.
#
# Although this method is simple and effective for small payloads, it relies on
# Data URLs, which are not ideal for large or binary content. In future versions,
# it may be preferable to offload download handling to the backend (e.g., via Django).
#
# Parameters
# ----------
# data : object
#     A small dictionary representing the dashboard’s state, typically stored in
#     the `status-data` component. This includes axis values, filter configurations,
#     and switch states.
#
# Returns
# -------
# str
#     An empty string upon successful trigger of the download process,
#     or `dash_clientside.no_update` if no action is taken.
#
# Behavior
# --------
# - Prompts the user to enter a filename (default: "status.json")
# - Converts the input data to a formatted JSON string
# - Creates a Blob and object URL for download
# - Triggers the download using a temporary anchor tag
# - Cleans up the temporary elements after the download completes
#
# Notes
# -----
# While the current solution provides a user-friendly browser-based download
# experience, it bypasses the native file save dialog and may not be ideal for
# production workflows. A more robust implementation using the File System Access API
# is also provided below (commented out), offering deeper integration with the
# operating system at the cost of browser compatibility and UI polish.
#
# Future versions may delegate this task to Django to provide cleaner handling,
# especially for larger payloads or authenticated sessions.

clientside_callback(
    """
    async function(data) {
        if (data) {
            try {
                const jsonString = JSON.stringify(data, null, 2);
                const blob = new Blob([jsonString], { type: 'application/json' });

                const filename = prompt("Please enter the filename:", "status.json"); // Get filename

                if (filename === null || filename.trim() === "") {
                    return window.dash_clientside.no_update;
                }

                const url = window.URL.createObjectURL(blob); // Create URL for blob

                const a = document.createElement('a');
                a.href = url;
                a.download = filename; // Set filename
                document.body.appendChild(a);
                a.click(); // Trigger download
                document.body.removeChild(a); // Clean up
                window.URL.revokeObjectURL(url); // Release blob URL

                return "";
            } catch (err) {
                console.error("Download error:", err);
                alert("Download failed. Please try again. Check the console for more details.");
                return window.dash_clientside.no_update;
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("dummy-div", 'children'),
    #---------------------
    Input("status-data", 'data'),
    #---------------------
    prevent_initial_call=True,
)

# """
#     async function(data) {
#         if (data) {
#             try {
#                 const jsonString = JSON.stringify(data, null, 2);
#                 const blob = new Blob([jsonString], { type: 'application/json' });

#                 // Let showSaveFilePicker handle the prompt:
#                 const handle = await window.showSaveFilePicker({ suggestedName: "data.json" }); // Suggested filename
#                 const writable = await handle.createWritable();
#                 await writable.write(blob);
#                 await writable.close();

#                 // Explicitly set handle to null to release access:
#                 handle = null; // Important: Release the handle!

#                 return "downloaded";
#             } catch (err) {
#                 console.error("Download error:", err);
#                 alert("Download failed. Please try again. Check the console for more details.");
#                 return window.dash_clientside.no_update;
#             }
#         }
#         return window.dash_clientside.no_update;
#     }
# """


@app.callback(
    Output("status-data", 'data'),
    #---------------------
    Input("save-status", 'n_clicks'),
    #---------------------
    State("x-axis-dropdown",'id'),
    State("x-axis-dropdown",'value'),
    State("y-axis-dropdown",'id'),
    State("y-axis-dropdown",'value'),
    State({"type": "filter-switch", "index": ALL}, 'id'),
    State({"type": "filter-switch", "index": ALL}, 'on'),
    State({"type": "filter-dropdown", "index": ALL}, 'id'),
    State({"type": "filter-dropdown", "index": ALL}, 'value'),
    State({"type": "filter-operator", "index": ALL}, 'id'),
    State({"type": "filter-operator", "index": ALL}, 'value'),
    State({"type": "filter-value", "index": ALL}, 'id'),
    State({"type": "filter-value", "index": ALL}, 'value'),
    State({"type": "second-filter-dropdown", "index": ALL}, 'id'),
    State({"type": "second-filter-dropdown", "index": ALL}, 'value'),
    State({"type": "second-filter-operator", "index": ALL}, 'id'),
    State({"type": "second-filter-operator", "index": ALL}, 'value'),
    State({"type": "second-filter-value", "index": ALL}, 'id'),
    State({"type": "second-filter-value", "index": ALL}, 'value'),
    State("channels",'id'),
    State("channels",'value'),
    State("show-filtered-data-switch", 'id'),
    State("show-filtered-data-switch", 'on'),
    State("fold-time-switch",'id'),
    State("fold-time-switch",'on'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def save_status(_,*args):
    """
    Save the current dashboard state, including axis selections and filter configurations.

    This function collects the current state of all dashboard controls—such as axis dropdowns,
    filters, channel selections, and switches—and assembles them into a dictionary suitable
    for export or persistent storage. It supports both primary and secondary filters.

    Parameters
    ----------
    _ : :class:`Any`
        Unused placeholder for the `n_clicks` input from the "save status" button.
    *args : :class:`list`
        Interleaved list of (id, value) pairs for all input states. Each id can either be a string
        (for global components like axis dropdowns and switches) or a dictionary (for indexed filters).

    Returns
    -------
    :class:`dict`
        A dictionary representing the current state of the dashboard, including:

        - Axis selection values.
        - All filters and their properties.
        - Active channels and switch states.

        The structure is compatible with later reloading via the :func:`load_status` function.
    """

    out_dict = {'filters':[]}
    for i,el in enumerate(args):
        if i%2==1: continue
        if type(args[i]) == list:
            for f,flt in enumerate(args[i]):
                while True:
                    if flt['index'] < len(out_dict['filters']):
                        break
                    else:
                        out_dict['filters'].append({'secondary':{}})
                if flt['type'].split('-')[0] == 'second':
                    out_dict['filters'][flt['index']]['secondary'][flt['type']] = args[i+1][f]
                else:
                    out_dict['filters'][flt['index']][flt['type']] = args[i+1][f]
        else:
            out_dict[args[i]] = args[i+1]
    return out_dict

@app.callback(
    Output("x-axis-dropdown",'value'),
    Output("y-axis-dropdown",'value'),
    Output("channels",'value'),
    Output("show-filtered-data-switch", 'on'),
    Output("fold-time-switch",'on'),
    Output("custom-filter-container",'children'),
    #---------------------
    Input("upload-status", 'contents'),
    #---------------------
    State("custom-filter-container",'children'),
    State("x-axis-dropdown",'options'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def load_status(contents, filter_div, labels):
    """
    Load a previously saved dashboard state from a base64-encoded JSON file.

    This function decodes and parses the uploaded status file and restores the application state,
    including axis selections, active channels, switches, and filters. It dynamically reconstructs
    each filter (both primary and secondary) and injects them into the dashboard.

    Parameters
    ----------
    contents : :class:`str`
        Base64-encoded string representing the uploaded file contents from the `Dash <https://dash.plotly.com/>`_ upload component.
    filter_div : :class:`list`
        List of existing filter components already present in the dashboard.
    labels : :class:`list`
        List of available labels used to populate new filters.

    Returns
    -------
    x_axis_value : :class:`str`
        Restored value for the x-axis dropdown.
    y_axis_value : :class:`str`
        Restored value for the y-axis dropdown.
    channels : :class:`list`
        Restored list of selected channels.
    show_filtered : :class:`bool`
        Whether to show filtered points, as restored from the saved state.
    fold_time : :class:`bool`
        Whether time-folding is enabled, as restored from the saved state.
    filter_div : :class:`list`
        Updated list of filter UI components reflecting the saved configuration.
    """
    decoded_string = base64.b64decode(contents.split(',')[1]).decode('utf-8')
    base64.b64decode(decoded_string)
    status_dict = json.loads(decoded_string)

    n_filter = len(filter_div)
    for f,flt in enumerate(status_dict['filters']):
        new_empty_filter = utils.new_empty_filter(n_filter+f, labels)

        filter_div.append(new_empty_filter)
        filter_div[-1].children[0].children[0].on = flt['filter-switch']
        filter_div[-1].children[0].children[1].value = flt['filter-dropdown']
        filter_div[-1].children[0].children[2].value = flt['filter-operator']
        filter_div[-1].children[0].children[3].value = flt['filter-value']

        if len(flt['secondary']) > 0:
            filter_div[-1].children[1].children = utils.new_empty_second_filter(n_filter+f, labels)

            filter_div[-1].children[1].children[1].value = flt['secondary']['second-filter-dropdown']
            filter_div[-1].children[1].children[2].value = flt['secondary']['second-filter-operator']
            filter_div[-1].children[1].children[3].value = flt['secondary']['second-filter-value']

    return status_dict["x-axis-dropdown"], status_dict["y-axis-dropdown"], status_dict["channels"], status_dict["show-filtered-data-switch"], status_dict["fold-time-switch"], filter_div


@app.callback(
    Output('selection-filter', 'disabled'),
    Input('main-plot', 'relayoutData'),
    State('main-plot', 'figure'),
    State("data-json",'data'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def update_filter_selection_state(relayout_data, fig, all_data):
    """
    Enable or disable the "Add Selection Filter" button based on current selection in the plot.

    This function checks whether a valid lasso or box selection exists in the main plot.
    If such a selection is detected (i.e., a non-empty path is present), the filter button
    becomes enabled; otherwise, it remains disabled.

    Parameters
    ----------
    relayout_data : :class:`dict`
        The relayout metadata from the Plotly plot, which may include a 'selections' field.
    fig : :class:`dict`
        The current figure displayed in the main plot (unused, but passed for context).
    all_data : :class:`dict`
        The full dataset shown in the dashboard (unused, but passed for context).

    Returns
    -------
    :class:`bool`
        `False` if a valid selection exists (enabling the button), `True` otherwise (disabling it).
    """

    if relayout_data and 'selections' in relayout_data:
        selection = relayout_data['selections']
        if isinstance(selection, list) and len(selection) > 0 and isinstance(selection[0], dict) and 'path' in selection[0]:
            return False
    return True


@app.callback(
    Output("custom-filter-container",'children', allow_duplicate=True),
    Output('main-plot', 'relayoutData'),
    Output('main-plot', 'figure', allow_duplicate=True),
    #---------------------
    Input("selection-filter",'n_clicks'),
    #---------------------
    State("custom-filter-container",'children'),
    State('main-plot', 'relayoutData'),
    State('main-plot', 'figure'),
    #---------------------
    prevent_initial_call=True
)
@utils.debug_print
def add_selection_filter(_, filter_div, relayout_data, figure):
    """
    Create and add a new filter based on the current selection region in the plot.

    This function checks if a valid lasso or box selection exists in the plot's ``relayoutData``.
    If so, it generates a new filter corresponding to the selected data points and appends it
    to the list of existing filters. The selection is then removed from the plot layout to avoid
    reprocessing.

    Parameters
    ----------
    _ : :class:`Any`
        Placeholder for the button click triggering the addition of a selection-based filter.
    filter_div : :class:`list`
        Existing list of `Dash <https://dash.plotly.com/>`_ filter components displayed in the UI.
    relayout_data : :class:`dict`
        Plotly relayout data containing information about lasso/box selections.
    figure : :class:`dict`
        The current figure dictionary shown in the main plot.

    Returns
    -------
    filter_div : :class:`list`
        Updated list of filter components, now including the new selection-based filter.
    relayoutData : :class:`dict`
        An empty dictionary to reset plot selection state.
    figure : :class:`dict`
        The updated figure with the selection metadata removed.
    """

    if not relayout_data or 'selections' not in relayout_data:
        return no_update, no_update, no_update

    selection = relayout_data['selections']
    if not isinstance(selection, list) or len(selection) == 0 or not isinstance(selection[0], dict) or 'path' not in selection[0]:
        return no_update, no_update, no_update


    del figure['layout']['selections']

    n_filter = len(filter_div)
    new_empty_filter = utils.new_selection_filter(n_filter, figure['data'][0]['selectedpoints'])
    filter_div.append(new_empty_filter)

    return filter_div, {}, figure