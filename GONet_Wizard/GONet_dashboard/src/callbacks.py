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
- :func:`exit_app` : Exit the entire application when the "Exit" button is clicked.

"""

import math

from dash import no_update, ctx, html
from dash.dependencies import Input, Output, State, ALL, MATCH

from GONet_Wizard.GONet_dashboard.src.server import app
from GONet_Wizard.GONet_dashboard.src import env
from GONet_Wizard.GONet_dashboard.src import utils
from GONet_Wizard.GONet_dashboard.src.hood import plot
from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import (
    load_json,
    register_json_download,
    register_staged_json_download,
    stage_json_download,
)
from GONet_Wizard.GONet_utils import DATA_SPEC


def _data_spec_keys(field_type):
    """Return canonical DATA_SPEC keys for one dashboard field category."""
    keys = []
    for fallback_key, field in DATA_SPEC.items():
        if getattr(field, "field_type", "env") != field_type:
            continue

        key = getattr(field, "key", fallback_key)
        if key not in keys:
            keys.append(key)
    return keys


def _json_safe_value(value):
    """Convert common dataframe scalar values to JSON-friendly objects."""
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if value is None:
        return None

    if isinstance(value, float) and not math.isfinite(value):
        return None

    if type(value).__name__ in {"NAType", "NaTType"}:
        return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass

    return value


def _build_export_records(df, epoch_indices):
    """Build nested export records from the loaded dashboard dataframe."""
    if df is None or df.empty or "epoch_idx" not in df.columns:
        return []

    has_col = df.columns.__contains__

    base_labels = []
    for label in ["filename", *_data_spec_keys("env")]:
        if label != "epoch_idx" and has_col(label) and label not in base_labels:
            base_labels.append(label)

    channel_labels = [
        label for label in _data_spec_keys("chn") if has_col(label)
    ]

    requested_indices = [] if epoch_indices is None else list(epoch_indices)
    if not requested_indices:
        return []

    required_columns = ["epoch_idx", *base_labels]
    if "channel" in df.columns:
        required_columns.append("channel")
    required_columns.extend(
        label for label in channel_labels if label not in required_columns
    )

    # Restrict the dataframe once. The previous implementation scanned the
    # complete dataframe separately for every epoch and then again for every
    # channel, which made export time grow rapidly with dataset size.
    selected = df.loc[
        df["epoch_idx"].isin(requested_indices),
        required_columns,
    ]
    if selected.empty:
        return []

    base_rows = selected.drop_duplicates("epoch_idx", keep="first")
    base_lookup = {
        row[0]: {
            label: _json_safe_value(value)
            for label, value in zip(base_labels, row[1:])
        }
        for row in base_rows[["epoch_idx", *base_labels]].itertuples(
            index=False,
            name=None,
        )
    }

    channel_lookups = {}
    if "channel" in selected.columns:
        for channel in env.CHANNELS:
            channel_rows = selected.loc[
                selected["channel"] == channel
            ].drop_duplicates("epoch_idx", keep="first")
            channel_lookups[channel] = {
                row[0]: {
                    label: _json_safe_value(value)
                    for label, value in zip(channel_labels, row[1:])
                }
                for row in channel_rows[
                    ["epoch_idx", *channel_labels]
                ].itertuples(index=False, name=None)
            }

    empty_channel = {label: None for label in channel_labels}
    records = []
    for epoch_idx in requested_indices:
        base_values = base_lookup.get(epoch_idx)
        if base_values is None:
            continue

        record = dict(base_values)
        for channel in env.CHANNELS:
            channel_values = channel_lookups.get(channel, {}).get(epoch_idx)
            record[channel] = (
                dict(channel_values)
                if channel_values is not None
                else dict(empty_channel)
            )
        records.append(record)

    return records


def _build_status_dict(args):
    """Group dashboard control values into a serializable status dictionary."""
    status = {}
    filters_by_index = {}
    filter_order = []

    for component_ids, values in zip(args[0::2], args[1::2]):
        if not isinstance(component_ids, list):
            if isinstance(component_ids, str):
                status[component_ids] = values
            continue

        value_list = values if isinstance(values, list) else []
        for component_id, value in zip(component_ids, value_list):
            if not isinstance(component_id, dict):
                continue

            raw_index = component_id.get("index")
            component_type = component_id.get("type")
            if raw_index is None or not isinstance(component_type, str):
                continue

            # Pattern-matching IDs may be integers in older saved layouts and
            # UUID-bearing strings in the current layout. Normalizing to text
            # avoids comparisons or sorting across incompatible Python types.
            index = str(raw_index)
            if index not in filters_by_index:
                filters_by_index[index] = {"secondary": {}}
                filter_order.append(index)

            filter_data = filters_by_index[index]
            if component_type.startswith("second-"):
                filter_data["secondary"][component_type] = value
            else:
                filter_data[component_type] = value

    status["filters"] = [filters_by_index[index] for index in filter_order]
    return status


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
    #---------------------
    prevent_initial_call=True
)
def update_main_plot(x_label, y_label, active_filters, channels, show_filtered_points, clickdata, fig, gonet_fig, info_table):
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
        fig = plot.FigureWrapper.build(x_label, y_label, channels, show_filtered_points, app.server.config["data"])
    else:
        # Rehydrate the figure to retain state (filtered points, big point, etc.)
        fig = plot.FigureWrapper.from_fig(fig, app.server.config["data"])

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

        # Attempt to render the corresponding image.  The dashboard reads the
        # full image path from the selected row's ``filename`` field, so no
        # separate image directory is required.
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

@utils.gonet_callback(
    Output("custom-filter-container", "children", allow_duplicate=True),
    # ---------------------
    Input({"type": "remove-filter", "index": ALL}, "n_clicks"),
    # ---------------------
    State("custom-filter-container", "children"),
    State({"type": "remove-filter", "index": ALL}, "id"),
    # ---------------------
    prevent_initial_call=True,
)
def remove_filter(n_clicks, filter_children, remove_ids):
    """
    Remove an entire filter block when its trash button is clicked.
    """
    
    # Which input triggered this callback?
    target_index = ctx.triggered_id.get("index")

    # Find the position of this button in the remove_ids list
    btn_pos = None
    for i, rid in enumerate(remove_ids):
        if rid.get("index") == target_index:
            btn_pos = i
            break

    # Only act if this button has actually been clicked
    # (on creation, n_clicks is 0)
    if not n_clicks[btn_pos] or n_clicks[btn_pos] <= 0:
        return no_update

    # Build new children list without the removed filter
    new_children = [
        child
        for child in filter_children
        if child.get("props", {}).get("id", {}).get("index") != target_index
    ]

    return new_children


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
    State({"type": "filter-switch", "index": ALL}, 'id'),
    State({"type": "filter-dropdown", "index": ALL}, 'id'),
    State({"type": "filter-dropdown", "index": ALL}, 'value'),
    State({"type": "filter-operator", "index": ALL}, 'id'),
    State({"type": "filter-value", "index": ALL}, 'id'),
    State({"type": "filter-selection-data", "index": ALL}, 'id'),
    State({"type": "second-filter-dropdown", "index": ALL}, 'id'),
    State({"type": "second-filter-dropdown", "index": ALL}, 'value'),
    State({"type": "second-filter-operator", "index": ALL}, 'id'),
    State({"type": "second-filter-value", "index": ALL}, 'id'),
    State("active-filters",'data'),
    #---------------------
    prevent_initial_call=True
)
def update_filters(
    _,
    switches,
    ops,
    values,
    selections,
    second_ops,
    second_values,
    switch_ids,
    label_ids,
    labels,
    op_ids,
    value_ids,
    selection_ids,
    second_label_ids,
    second_labels,
    second_op_ids,
    second_value_ids,
    filters_before,
):
    """
    Assemble and update the active filters list from the current filter UI state.

    The dashboard has two filter types:

    - ordinary value filters, which have a ``filter-value`` component;
    - selection filters, which store selected ``epoch_idx`` values in a
      ``filter-selection-data`` store and therefore do not have a
      ``filter-value`` component.

    Because those two filter types do not expose the same pattern-matching
    components, this callback aligns all inputs by their component ``index`` IDs
    rather than by list position. That makes mixed value filters and selection
    filters safe to add, remove, toggle, and combine.
    """

    def activate_show_filters(active_filters):
        if len(active_filters) > 0:
            return False, True
        else:
            return True, True

    def has_value(value):
        """Return True when a filter value should be considered present."""
        if value is None:
            return False
        if isinstance(value, str) and value == "":
            return False
        if isinstance(value, (list, tuple, set)) and len(value) == 0:
            return False
        return True

    def index_from_id(id_):
        """Extract the pattern-matching index from a Dash component ID."""
        return id_.get("index") if isinstance(id_, dict) else None

    def map_by_index(ids, vals):
        """Build an index -> value mapping from aligned Dash ALL inputs."""
        out = {}
        for id_, val in zip(ids or [], vals or []):
            idx = index_from_id(id_)
            if idx is not None:
                out[idx] = val
        return out

    label_by_index = map_by_index(label_ids, labels)
    op_by_index = map_by_index(op_ids, ops)
    value_by_index = map_by_index(value_ids, values)
    selection_by_index = map_by_index(selection_ids, selections)
    second_label_by_index = map_by_index(second_label_ids, second_labels)
    second_op_by_index = map_by_index(second_op_ids, second_ops)
    second_value_by_index = map_by_index(second_value_ids, second_values)

    active_filters = []

    for switch_id, switch_on in zip(switch_ids or [], switches or []):
        idx = index_from_id(switch_id)
        if idx is None:
            continue

        label = label_by_index.get(idx)
        op = op_by_index.get(idx)

        if idx in selection_by_index:
            value = selection_by_index.get(idx)
        else:
            value = value_by_index.get(idx)

        if switch_on and label is not None and op is not None and has_value(value):
            # Convert date/time filters to the internal numeric quantities used
            # by the loaded dataframe. Selection filters keep the ``Selection``
            # label and epoch-index list unchanged.
            label, value = utils.parse_date_time(label, value)

            active_filters.append({'label': label, 'operator': op, 'value': value})

            if idx in second_label_by_index:
                second_label = second_label_by_index.get(idx)
                second_op = second_op_by_index.get(idx)
                second_value = second_value_by_index.get(idx)

                if second_label is not None and second_op is not None and has_value(second_value):
                    second_label, second_value = utils.parse_date_time(second_label, second_value)
                    active_filters[-1]['secondary'] = {
                        'label': second_label,
                        'operator': second_op,
                        'value': second_value,
                    }

    if filters_before != active_filters:
        return active_filters, *activate_show_filters(active_filters)
    else:
        return no_update, no_update, no_update

app.clientside_callback(
    """
    function(nClicks, figure) {
        if (!nClicks || !figure) {
            return window.dash_clientside.no_update;
        }

        const traces = Array.isArray(figure.data) ? figure.data : [];
        const visibleTrace = traces.find(
            trace => !trace.filtered && !trace.big_point
        );
        const epochIndices = visibleTrace && Array.isArray(visibleTrace.epoch_idx)
            ? visibleTrace.epoch_idx
            : [];

        return {
            request_id: nClicks,
            epoch_indices: epochIndices
        };
    }
    """,
    Output("export-epoch-indices", "data"),
    Input("export-data", "n_clicks"),
    State("main-plot", "figure"),
    prevent_initial_call=True,
)


@utils.gonet_callback(
    Output("export-data-json", "data"),
    # ---------------------
    Input("export-epoch-indices", "data"),
    # ---------------------
    prevent_initial_call=True,
)
def export_data(export_request):
    """
    Export filtered data from the plot to a downloadable JSON file.

    This function retrieves all points currently visible in the main plot that are not
    filtered or marked as big points. It extracts relevant metadata and fit parameters
    for each unique index across all channels, organizing the data into a structured JSON
    format for export.

    Parameters
    ----------
    export_request : :class:`dict`
        Small client-generated request containing the visible ``epoch_idx``
        values and a monotonically increasing request identifier.
    Returns
    -------
    :class:`dict`
        Descriptor for the staged JSON payload. The clientside save callback
        uses the one-time local URL without sending the full export through a
        Dash store or the pywebview bridge.

    """

    df = app.server.config["data"]

    epoch_indices = (export_request or {}).get("epoch_indices", [])
    json_out = _build_export_records(df, epoch_indices)

    return stage_json_download(json_out, "filtered_data.json")


register_staged_json_download(
    app,
    Output("export-save-dummy", 'children'),
    #---------------------
    Input("export-data-json", 'data'),
    default_filename="filtered_data.json",
)

register_json_download(
    app,
    Output("status-save-dummy", 'children'),
    #---------------------
    Input("status-data", 'data'),
    default_filename="dashboard_status.json",
)


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
    State({"type": "filter-selection-data", "index": ALL}, 'id'),
    State({"type": "filter-selection-data", "index": ALL}, 'data'),
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

    return _build_status_dict(args)

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
    for offset, saved_filter in enumerate(status_dict.get("filters", [])):
        new_index = n_filter + offset
        selection_data = saved_filter.get("filter-selection-data")

        if selection_data is not None:
            new_filter = utils.new_selection_filter(new_index, selection_data)
            new_filter.children[0].children[0].children.on = saved_filter.get(
                "filter-switch", False
            )
            new_filter.children[0].children[3].value = saved_filter.get(
                "filter-operator", "in"
            )
            filter_div.append(new_filter)
            continue

        new_filter = utils.new_empty_filter(new_index, labels)
        first_row = new_filter.children[0].children
        first_row[0].children.on = saved_filter.get("filter-switch", False)
        first_row[1].value = saved_filter.get("filter-dropdown")
        first_row[2].value = saved_filter.get("filter-operator", env.DEFAULT_OP)
        first_row[3].value = saved_filter.get("filter-value")

        secondary = saved_filter.get("secondary") or {}
        if secondary:
            new_filter.children[1].children = utils.new_empty_second_filter(
                new_filter.id["index"], labels
            )
            second_row = new_filter.children[1].children
            second_row[1].value = secondary.get("second-filter-dropdown")
            second_row[2].value = secondary.get(
                "second-filter-operator", env.DEFAULT_OP
            )
            second_row[3].value = secondary.get("second-filter-value")

        filter_div.append(new_filter)

    return (
        status_dict.get("x-axis-dropdown"),
        status_dict.get("y-axis-dropdown"),
        status_dict.get("channels", list(env.CHANNELS)),
        status_dict.get("show-filtered-data-switch", True),
        filter_div,
    )


@utils.gonet_callback(
    Output('selection-filter', 'disabled'),
    #---------------------
    Input('main-plot', 'relayoutData'),
    #---------------------
    prevent_initial_call=True
)
def update_filter_selection_state(relayout_data):
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

    Plotly stores lasso/box selections as point positions within each trace. The
    dashboard filters data using ``epoch_idx`` values, so this callback converts
    selected trace positions into the corresponding epoch indices before storing
    the selection filter.

    Parameters
    ----------
    _ : :class:`Any`
        Placeholder for the button click triggering the addition of a selection-based filter.
    filter_div : :class:`list`
        Existing list of filter components displayed in the UI.
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
        The updated figure with selection metadata removed.
    """

    def selected_epoch_indices(fig):
        """Collect selected epoch indices from every selected trace."""
        selected = []
        for trace in fig.get('data', []):
            if trace.get('big_point'):
                continue

            selected_points = trace.get('selectedpoints')
            if selected_points is None:
                continue

            epoch_idx = trace.get('epoch_idx', [])
            for point_number in selected_points:
                try:
                    epoch_value = epoch_idx[int(point_number)]
                except (TypeError, ValueError, IndexError):
                    continue

                # Make numpy scalar values JSON-serializable while preserving
                # string-like ids if they ever appear.
                if hasattr(epoch_value, 'item'):
                    epoch_value = epoch_value.item()
                selected.append(epoch_value)

        # Deduplicate while preserving order. A lasso can select the same epoch
        # in multiple channel traces.
        return list(dict.fromkeys(selected))

    if not relayout_data or 'selections' not in relayout_data:
        return no_update, no_update, no_update

    selection = relayout_data['selections']
    if not isinstance(selection, list) or len(selection) == 0 or not isinstance(selection[0], dict) or 'path' not in selection[0]:
        return no_update, no_update, no_update

    selected_epochs = selected_epoch_indices(figure)
    if len(selected_epochs) == 0:
        return no_update, no_update, no_update

    # Remove the visual selection outline and trace-level selectedpoints so the
    # plot returns to a neutral state after the selection filter is created.
    figure.get('layout', {}).pop('selections', None)
    for trace in figure.get('data', []):
        trace.pop('selectedpoints', None)

    n_filter = len(filter_div)
    new_empty_filter = utils.new_selection_filter(n_filter, selected_epochs)
    filter_div.append(new_empty_filter)

    return filter_div, {}, figure


@app.callback(
    Output("exit-button", "disabled"),  # dummy output
    #---------------------
    Input("exit-button", "n_clicks"),
    #---------------------
    prevent_initial_call=True
)
def exit_app(_):
    """
    Callback to request closing the PyWebView window when the "Exit" button is clicked.

    This callback sends a JavaScript command to the embedded PyWebView browser,
    which calls the exposed Python API method ``close_window()`` to close the window.

    Parameters
    ----------
    _ : :class:`int` or :class:`NoneType`
        Click count of the "Exit" button (ignored).

    Returns
    -------
    :class:`bool`
        Always returns ``True`` to disable the "Exit" button after it has been clicked.
    """
    from GONet_Wizard.ui import WINDOWS
    WINDOWS.close("dashboard")
    return True