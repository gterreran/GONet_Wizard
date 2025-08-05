"""
Callbacks for the GONet Dashboard.

This module defines all `Dash <https://dash.plotly.com/>`_ callback functions that power the interactivity
of the GONet Wizard dashboard. The callbacks handle core responsibilities such as:

- Loading and parsing the GONet data archive
- Applying and managing user-defined filters
- Generating interactive plots and statistics
- Managing UI state, selections, and saved configurations
- Exporting data and application state to JSON

**Callback Registration Decorators**

Most callbacks in this module use the custom :func:`utils.gonet_callback` decorator, which extends
Dash’s default callback mechanism to include:

- Automatic alert handling (via the `alert-container`)
- Inline warning and exception capture
- Debug logging (including the triggering input and source line)

This greatly simplifies development and debugging, especially for callbacks that modify user-facing
components like figures and tables.

**⚠️ Important Exception: MATCH/ALL Pattern-Matching Callbacks**

Dash requires all Outputs in a callback to use the same wildcard keys when using pattern-matching IDs
(`MATCH`, `ALL`, etc.). Since :func:`utils.gonet_callback` automatically adds static alert outputs,
it **cannot** be used with callbacks that include pattern-matching outputs.

For these cases, such as:

.. code-block:: python

    Output({"type": "filter-value", "index": MATCH}, "value")

we used instead:

- :func:`app.callback` directly
- Decorate the callback with :func:`utils.debug_print` for logging

This ensures compatibility with Dash's output constraints and avoids runtime errors.


**Functions**

- :func:`load` : Load available data from the configured ROOT directory and prepare dropdown options.
- :func:`update_main_plot` : Update the main plot based on the selected axes, filters, and other plot parameters.
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
from dash.dependencies import Input, Output, State, ALL, MATCH

from GONet_Wizard.GONet_dashboard.src.server import app
from GONet_Wizard.GONet_dashboard.src import env
from GONet_Wizard.GONet_dashboard.src import utils
from GONet_Wizard.GONet_dashboard.src.hood import load_data
from GONet_Wizard.GONet_dashboard.src.hood import plot
from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import register_json_download, load_json


@utils.gonet_callback(
    Output('data-json', 'data'),
    Output("x-axis-dropdown",'options'),
    Output("y-axis-dropdown",'options'),
    #---------------------
    Input("top-container",'children'),
    #---------------------
    prevent_initial_call='initial_duplicate'
)
def load(_):
    """
    Dash callback to initialize the dashboard data store and dropdown options.

    This function is triggered once when the layout is rendered. It delegates the
    actual data-loading logic to :func:`load_data.load_data_from_json`, which scans the directory
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

    """


    all_data = load_data.load_data_from_json(env)

    labels_dropdown = [
        {"label": l, "value": l}
        for l in env.LABELS['gen'] + env.LABELS['fit']
        if l != 'filename'
    ]

    return all_data, labels_dropdown, labels_dropdown


@utils.gonet_callback(
    Output("main-plot",'figure'),
    Output("stats-table", 'children'),
    Output("gonet-image",'figure'),
    Output("info-table",'children'),
    #---------------------
    Input("x-axis-dropdown",'value'),
    Input("y-axis-dropdown",'value'),
    Input("active-filters",'data'),
    Input("channels",'value'),
    Input("show-filtered-data-switch", 'on'),
    Input("main-plot",'clickData'),
    #---------------------
    State("main-plot",'figure'),
    State("gonet-image",'figure'),
    State("info-table",'children'),
    State("data-json",'data'),
    #---------------------
    prevent_initial_call=True
)
def update_main_plot(x_label, y_label, active_filters, channels, show_filtered_points, clickdata, fig, gonet_fig, info_table, all_data):
    """
    Update the main plot, statistics table, image preview, and info panel in response to user interaction.

    This is the central callback for GONet dashboard interactivity. It responds to any change
    that affects how data should be visualized or interpreted, and coordinates all downstream
    updates accordingly. It ensures that the displayed figure remains synchronized with the
    current filter set, axis choices, selected channels, and clicked data point.

    Triggers that activate this callback include:

    - Changing the selected x- or y-axis quantity
    - Adding, removing, or modifying any active filters
    - Toggling the visibility of filtered-out points
    - Enabling or disabling channels in the channel selector
    - Clicking a data point on the plot

    This function manages the following visual components:

    - The main scatter plot (created or updated using :class:`FigureWrapper`)
    - The statistics summary table (mean ± std for x and y values)
    - The GONet image heatmap of the selected "big point" (if applicable)
    - The information table containing metadata for the selected data point

    Depending on the triggering input, the function will:

    - Rebuild the entire figure from scratch (on axis change)
    - Reapply filters and update trace visibility (on filter change)
    - Show or hide filtered-out points (on toggle)
    - Add or remove traces corresponding to visible channels (on channel change)
    - Highlight and load image + metadata for the selected point (on click)

    Parameters
    ----------
    x_label : :class:`str`
        Selected label for the x-axis (e.g., 'sky_brightness').
    y_label : :class:`str`
        Selected label for the y-axis (e.g., 'temperature').
    active_filters : :class:`list` of :class:`dict`
        User-defined filters to apply to the dataset. Each filter includes a label, operator, and value.
    channels : :class:`list` of :class:`str`
        List of active channels to display (e.g., ['red', 'green', 'blue']).
    show_filtered_points : :class:`bool`
        Whether to display data points that fail the filter criteria with reduced opacity.
    clickdata : :class:`dict` or :class:`None`
        Plotly clickData object containing information about the clicked point (if any).
    fig : :class:`dict`
        Current Plotly figure, passed in from the Dash state.
    gonet_fig : :class:`dict`
        Current heatmap image figure, passed in from the Dash state.
    info_table : :class:`list`
        Current info table rows, passed in from the Dash state.
    all_data : :class:`dict`
        Complete flattened dataset returned by :func:`load_data_from_json`.

    Returns
    -------
    :class:`dict`
        Updated Plotly figure reflecting current filters, axes, and channels.
    :class:`list`
        Updated statistics table rows with mean and standard deviation summaries.
    :class:`dict` or :data:`dash.no_update`
        Updated heatmap figure or :data:`dash.no_update` if no change is needed.
    :class:`list`
        Updated rows of the data point information table.
    """
    
    if x_label is None or y_label is None:
        # If axes are not yet selected, abort update
        return no_update, no_update, no_update, no_update

    if ctx.triggered_id in ['x-axis-dropdown', 'y-axis-dropdown']:
        # Axes changed → build a new figure from scratch
        fig = plot.FigureWrapper.build(x_label, y_label, channels, all_data)
    else:
        # Rehydrate the figure to retain state (filtered points, big point, etc.)
        fig = plot.FigureWrapper.from_fig(fig, all_data)

    # Apply filters to the dataset
    fig.update_filters(active_filters)
    for c in fig.channels:
        fig.filter_traces(c)

    # Toggle visibility of filtered points
    if ctx.triggered_id == 'show-filtered-data-switch':
        fig.update_visibility(show_filtered_points)
        fig.apply_visibility()

    # Add or remove channel traces
    if ctx.triggered_id == 'channels':
        fig.update_channels(channels)

    # Generate statistics summary table
    formatted_stats_table = [
        html.Tr([html.Td(el[val]) for el in fig.get_stats()[axis] for val in ['label', 'value']])
        for axis in ['x', 'y']
    ]

    # Handle data point selection ("big point")
    if ctx.triggered_id == 'main-plot':
        fig.gather_big_point(clickdata)
        fig.plot_big_point()

        # Extract point-specific metadata
        info_dictionary = fig.get_data_point_info()
        info_table = [html.Tr([html.Td(el), html.Td(info_dictionary[el])]) for el in info_dictionary]

        # Attempt to render the corresponding image
        gonet_fig = fig.gonet_image(clickdata)
        if gonet_fig is None:
            gonet_fig = no_update

    return fig.to_dict(), formatted_stats_table, gonet_fig, info_table
            

@utils.gonet_callback(
    Output("custom-filter-container",'children', allow_duplicate=True),
    #---------------------
    Input("add-filter",'n_clicks'),
    #---------------------
    State("custom-filter-container",'children'),
    State("x-axis-dropdown",'options'),
    #---------------------
    prevent_initial_call=True
)
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
    

@utils.gonet_callback(
    Output("active-filters",'data'),
    Output("show-filtered-data-switch",'disabled'),
    Output("show-filtered-data-switch",'on'),
    #---------------------
    Input('data-json', 'data'),
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
def update_filters(_, switches, ops, values, selections, second_ops, second_values, labels, second_labels, second_ids, selections_ids, filters_before):
    """
    Assemble and update the active filters list based on user-defined filter inputs.

    This function collects the current state of all active filters, including their
    labels, operators, and values, and constructs a list of active filters. If a
    secondary (OR) filter is present, it is added as a nested dictionary.

    This function is also triggered at load up. Since initially ``active_filters``
    is ``None``, when triggered the `show-filtered-data-switch` is reset to default
    status. 

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

    def activate_show_filters(active_filters):
        if len(active_filters) > 0:
            return False, True
        else:
            return True, True

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

        label = labels[i]
        op = ops[i]

        if s and label is not None and value is not None:
            # converting date filters to unix time for an easier comparison
            label, value = utils.parse_date_time(label, value)

            active_filters.append({'label': label, 'operator': op, 'value': value})
            for j,id in enumerate(second_ids):

                second_label = second_labels[j]
                second_op = second_ops[j]
                second_value = second_values[j]

                if id['index'] == i and second_label is not None and second_value is not None:
                    second_label, second_value = utils.parse_date_time(second_label, second_value)
                    active_filters[-1]['secondary'] = {'label': second_label, 'operator': second_op, 'value': second_value}

    if filters_before != active_filters:
        return active_filters, *activate_show_filters(active_filters)
    else:
        return no_update, no_update, no_update



@utils.gonet_callback(
    Output("download-json", 'data'),
    #---------------------
    Input("export-data", 'n_clicks'),
    #---------------------
    State("main-plot",'figure'),
    State("data-json",'data'),
    #---------------------
    prevent_initial_call=True
)
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

register_json_download(
    app,
    Output("dummy-div", 'children'),
    #---------------------
    Input("status-data", 'data'),
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


@utils.gonet_callback(
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
    #---------------------
    prevent_initial_call=True
)
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

@utils.gonet_callback(
    Output("x-axis-dropdown",'value', allow_duplicate=True),
    Output("y-axis-dropdown",'value'),
    Output("channels",'value'),
    Output("show-filtered-data-switch", 'on', allow_duplicate=True),
    Output("custom-filter-container",'children'),
    #---------------------
    Input("upload-status", 'contents'),
    #---------------------
    State("custom-filter-container",'children'),
    State("x-axis-dropdown",'options'),
    #---------------------
    prevent_initial_call=True
)
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
    filter_div : :class:`list`
        Updated list of filter UI components reflecting the saved configuration.
    """
    
    status_dict = load_json(contents)

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

    return status_dict["x-axis-dropdown"], status_dict["y-axis-dropdown"], status_dict["channels"], status_dict["show-filtered-data-switch"], filter_div


@utils.gonet_callback(
    Output('selection-filter', 'disabled'),
    Input('main-plot', 'relayoutData'),
    State('main-plot', 'figure'),
    State("data-json",'data'),
    #---------------------
    prevent_initial_call=True
)
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


@utils.gonet_callback(
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