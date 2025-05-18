"""
Plot utilities for interactive visualization of GONet sky monitoring data.

This module provides Plotly-compatible wrappers and helper classes for rendering,
filtering, and interacting with GONet dashboard plots in a Dash application. It
includes specialized data structures that extend standard Python types (e.g., `dict`)
to support reactive behavior, styling changes, and integration with user inputs
like selections and click events.

**Classes**

- :class:`Trace`:
    A dictionary-like wrapper for a single Plotly scatter trace with built-in
    styling logic tied to filter and visibility states. Automatically updates
    marker opacity and hover behavior when `filtered` or `hidden` flags are set.

- :class:`FigureWrapper`:
    A manager class that encapsulates a complete Plotly figure dictionary and
    provides high-level methods for trace filtering, channel updates, visibility
    toggling, point selection, and summary statistics. Designed to maintain
    JSON-serializability for use in Dash callbacks.

This module is intended to serve as the plotting backend for the GONet dashboard UI.
"""

import numpy as np
import warnings

from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_dashboard.src import env


class Trace(dict):
    """
    A specialized dictionary-like object representing a single Plotly scatter trace
    with automatic styling and visibility behavior. This class is intended to be used
    in applications like Dash where Plotly figures must remain JSON-serializable, but
    where it is useful to treat individual traces as stateful, reactive objects.

    This wrapper class auto-initializes a full trace structure upon creation, and 
    includes logic to modify the trace's appearance when certain semantic fields
    (``filtered``, ``hidden``) are updated.

    Reactive Key Behaviors
    -------------------------

    - Setting `filtered = True`:
        - Reduces marker opacity to 0.2.
    - Setting `filtered = False`:
        - Restores marker opacity to 1.0.
    - Setting `hidden = True`:
        - Sets marker opacity to 0 (fully transparent),
        - Disables hover information,
        - Sets marker line width to 0 (if applicable).
    - Setting `hidden = False`:
        - Sets opacity back to 0.2 (like a filtered trace),
        - Restores hover information and hovertemplate,
        - Sets marker line width to 2 (if applicable).
    - Changing the ``marker`` key will automatically change
      the ``unselected`` marker as well.

    Notes
    -------------------------

    - This class behaves like a dictionary and can be appended directly to a Plotly
      figure's `data` list.
    - It is fully JSON-serializable and can be passed to Dash components.
    - You must use this class instead of a plain dictionary if you want the special
      reactive behavior described above.
      
    """

    def __init__(self, x_label: str, y_label: str, channel: str):
        """
        Initialize a new Trace object representing a styled Plotly scatter trace.

        This constructor populates the trace with default settings and metadata
        necessary for integration with the GONet dashboard, including a custom
        hovertemplate, marker styling, and semantic keys such as `filtered`, `hidden`,
        and `big_point`.

        Parameters
        ----------
        x_label : :class:`str`
            The label for the x-axis quantity. Used in the hovertemplate.
        y_label : :class:`str`
            The label for the y-axis quantity. Used in the hovertemplate.
        channel : :class:`str`
            The name of the channel this trace represents (e.g., 'red', 'green', 'blue').
            Used for trace naming, grouping, and color selection.

        """
        super().__init__()

        self.x_label = x_label
        self.y_label = y_label

        marker = {
            'color': env.rgba(channel=channel, alpha=1),
            'symbol': 'circle'
        }

        self.update({
            'hovertemplate': f"{x_label}=%{{x}}<br>{y_label}=%{{y}}",
            'x': [],
            'y': [],
            'type': 'scatter',
            'mode': 'markers',
            'marker': marker,
            'unselected': {'marker': marker},
            'channel': channel,
            'name': channel,
            'showlegend': True,
            'idx': [],
            'filtered': False,
            'big_point': False,
            'hidden': False,
        })

    def __setitem__(self, key, value):
        """
        Override assignment to specific trace keys to enable reactive styling behavior.

        This method extends dictionary-style item assignment (`trace[key] = value`)
        with special handling for keys such as `filtered`, `hidden`, and `marker`,
        allowing the trace to dynamically update its visual properties in response
        to filtering and selection logic.

        Parameters
        ----------
        key : :class:`str`
            The key to assign in the trace dictionary. May be a standard Plotly trace key
            or a semantic extension (e.g., 'filtered', 'hidden').
        value : any
            The value to assign to the key.

        Special Key Behaviors
        ---------------------

        - `'filtered'`:
            Updates marker color opacity to 0.2 (True) or 1.0 (False) using `env.rgba`.
        - `'hidden'`:
            If True:

                - Sets marker opacity to 0 (invisible)
                - Disables hover behavior
                - Hides marker outlines (if present)

            If False:

                - Sets marker opacity to 0.2
                - Restores hover behavior and marker line width
                
        - `'marker'`:
            Automatically syncs `unselected.marker` with the new marker value.

        """
        if key == 'filtered':
            alpha = 0.2 if value else 1
            self['marker']['color'] = env.rgba(channel=self['channel'], alpha=alpha)
            self['unselected']['marker']['color'] = env.rgba(channel=self['channel'], alpha=alpha)

        if key == 'hidden':
            if value:
                self['marker']['color'] = env.rgba(channel=self['channel'], alpha=0)
                self['hoverinfo'] = "none"
                self['hovertemplate'] = None
                if 'line' in self['marker']:
                    self['marker']['line']['width']=0
            else:
                self['marker']['color'] = env.rgba(channel=self['channel'], alpha=0.2)
                self['hoverinfo'] = "x+y+text+channel"
                self['hovertemplate'] = self.x_label+'=%{x}<br>'+self.y_label+'=%{y}'
                if 'line' in self['marker']:
                    self['marker']['line']['width']=2

        if key == 'marker':
            self['unselected'] = {'marker': value}

        super().__setitem__(key, value)

    

class FigureWrapper:
    """
    A stateful wrapper around a Plotly figure dictionary for interactive visualization 
    in the GONet dashboard.

    This class manages trace creation, filtering, visibility toggling, and interactivity
    for a multi-channel Plotly scatter plot. It provides a high-level API to dynamically
    update plots in response to user interactions (e.g., selection filters, click events,
    channel switching) while maintaining JSON-compatibility for use in Dash callbacks.

    Key Features
    ------------

    - Stores a reference to the full data (`all_data`) and x/y labels
    - Tracks currently plotted channels and filter state
    - Separates traces into normal, filtered, and big-point variants per channel
    - Automatically updates trace styling and visibility when filters change
    - Supports reconstruction from serialized figures (`from_fig`)
    - Integrates with environment configuration (e.g., colors, filter ops)

    Recommended Entry Point
    ------------------------
    Use :meth:`FigureWrapper.build` to initialize a fresh figure and add traces
    for each channel. Alternatively, use :meth:`from_fig` to restore a figure
    after a Dash callback round trip.

    Attributes
    ----------
    fig : :class:`dict`
        The full Plotly figure dictionary (layout + traces), modified in-place.
    x_label : :class:`str`
        Name of the data field plotted on the x-axis.
    y_label : :class:`str`
        Name of the data field plotted on the y-axis.
    all_data : :class:`dict`
        Full GONet dataset used for plotting, including x/y values, filters, and channels.
    channels : :class:`list` of :class:`str`
        Currently visible channels in the figure.
    total_filter : np.ndarray
        Boolean array (same length as data) representing active filtering state.
    show_filtered_points : bool
        Whether to display filtered-out points with reduced opacity or hide them entirely.
    big_point_idx : int or None
        Index of the currently selected “big point” for highlighting and image preview.

    Notes
    -----
    - Each channel has three associated traces: visible, filtered, and big-point.
    - Traces are dynamically updated using `filter_traces`, `update_filters`, and `apply_visibility`.
    - All traces are Plotly- and Dash-compatible (JSON-serializable).

    """

    def __init__(self, fig: dict, x_label: str, y_label: str, all_data: dict):
        """
        Initialize a :class:`FigureWrapper` with an existing Plotly figure and data source.

        This constructor sets up the internal state of the wrapper using an existing
        Plotly figure dictionary, axis labels, and the full dataset. It initializes
        filters, channel tracking, and big-point selection support.

        Parameters
        ----------
        fig : :class:`dict`
            A Plotly-compatible figure dictionary. This should contain a `layout` key with
            axis configurations and a `data` list for trace dictionaries or Trace objects.
        x_label : :class:`str`
            The field name used for the x-axis (must be a key in `all_data`).
        y_label : :class:`str`
            The field name used for the y-axis (must be a key in `all_data`).
        all_data : :class:`dict`
            The full data dictionary used by the dashboard. It should contain at minimum:

            - `'channel'`: array of channel labels
            - `'idx'`: array of global image indices
            - All fields needed for plotting and filtering

        """
        self.fig = fig
        self.x_label = x_label
        self.y_label = y_label
        self.all_data = all_data
        self.channels = []
        self.total_filter = np.full(len(all_data['channel']), True)
        self.show_filtered_points = True
        self.big_point_idx = None


    @classmethod
    def build(cls, x_label: str, y_label: str, channels: list, all_data: dict):
        """
        Construct a new :class:`FigureWrapper` with default layout and one trace per channel.

        This method initializes a Plotly figure dictionary with a standardized layout and styling
        settings based on the GONet dashboard environment. It then creates a new 
        :class:`FigureWrapper` instance and populates it with traces for each requested channel.

        If both `x_label` and `y_label` refer to general (non-channel-specific) quantities,
        only a single trace is created using channel `"gen"` as a placeholder.

        Parameters
        ----------
        x_label : :class:`str`
            The quantity to be used for the x-axis. This must be a key in `all_data`.
        y_label : :class:`str`
            The quantity to be used for the y-axis. This must be a key in `all_data`.
        channels : :class:`list` of :class:`str`
            A list of channel names (e.g., `['red', 'green', 'blue']`) to generate traces for.
        all_data : :class:`dict`
            The full dataset dictionary containing:

            - `'idx'`: global index values
            - All fields referenced by `x_label`, `y_label`, and filters

        Returns
        -------
        FigureWrapper
            A new wrapper object containing the initialized figure and all traces.

        Notes
        -----
        - Time-based x-labels (starting with `'hours_'`) are formatted as HH:MM.
        - The method uses `env.LABELS['gen']` to determine if the selected axes are non-channel-specific.
        - This is the standard entry point for figure creation at the beginning of a session.

        """
        fig = {
            'data': [],
            'layout': {
                'paper_bgcolor': env.BG_COLOR,
                'plot_bgcolor': env.BG_COLOR,
                'font': {'color': env.TEXT_COLOR},
                'dragmode': 'lasso',
                'margin': {'l': 10, 'r': 10, 't': 10, 'b': 10},
                'xaxis': {
                    'title': {'text': x_label},
                    'automargin': True,
                    'ticks': "outside",
                    'mirror': True
                },
                'yaxis': {
                    'title': {'text': y_label},
                    'automargin': True,
                    'ticks': "outside",
                    'mirror': True
                },
            }
        }

        if x_label.split('_')[0]=='hours':
            fig['layout']['xaxis']['tickformat'] = "%H:%M"

        wrapper = cls(
            fig=fig,
            x_label=x_label,
            y_label=y_label,
            all_data=all_data
        )


        if x_label in env.LABELS['gen'] and y_label in env.LABELS['gen']:
            # If the labels are not channel-specific, the row of any channel can be used
            channels = ['gen']

        for c in channels:
            # Add the initial traces here
            wrapper.add_trace(c)

        return wrapper
    

    @classmethod
    def from_fig(cls, fig: dict, all_data: dict):
        """
        Reconstruct a :class:`FigureWrapper` from an existing Plotly figure dictionary.

        This method is used to rehydrate a previously serialized Plotly figure back into
        a fully functional :class:`FigureWrapper` instance. It restores internal logic
        such as:

        - Trace interactivity via the :class:`Trace` wrapper
        - Active channels
        - Selection state (`big_point_idx`)
        - Visibility toggle for filtered points

        Parameters
        ----------
        fig : :class:`dict`
            A Plotly-compatible figure dictionary, typically from a callback.
            It must include:

            - 'layout': with axis title strings under `xaxis.title.text` and `yaxis.title.text`
            - 'data': a list of trace dictionaries, each with at least a 'channel' field

        all_data : :class:`dict`
            The full dataset originally used to construct the figure, including the keys
            referenced by each trace's 'x', 'y', and 'idx' attributes. This is needed to
            restore filtering, indexing, and interactivity.

        Returns
        -------
        FigureWrapper
            A fully reconstructed FigureWrapper with trace semantics, filter states,
            and internal configuration restored.

        Notes
        -----

        - Each trace in `fig['data']` is converted into a :class:`Trace` object.
        - Channels are inferred from the 'channel' field in each trace.
        - If a trace is marked as `big_point`, its associated `idx[0]` is stored as `big_point_idx`.
        - If any trace is marked as `hidden`, `show_filtered_points` is set to False.
        - This method assumes that all necessary metadata exists in the figure dictionary
          and that `all_data` is consistent with what was used to generate the figure.

        """
        x_label = fig['layout']['xaxis']['title']['text']
        y_label = fig['layout']['yaxis']['title']['text']

        # Convert each trace to a Trace instance for reactive behavior
        converted_traces = []
        for trace in fig['data']:
            trace_obj = Trace(x_label=x_label, y_label=y_label, channel=trace['channel'])
            trace_obj.update(trace)  # Apply original trace content
            converted_traces.append(trace_obj)

        fig['data'] = converted_traces

        # Instantiate the wrapper with restored state
        wrapper = cls(
            fig=fig,
            x_label=x_label,
            y_label=y_label,
            all_data=all_data
        )

        # Recover internal state from trace attributes
        for img in fig['data']:
            if img['channel'] not in wrapper.channels:
                wrapper.channels.append(img['channel'])
            if img['big_point']:
                if len(img['idx']) > 0:
                    wrapper.big_point_idx = img['idx'][0]
            if img['hidden']:
                wrapper.show_filtered_points = False

        return wrapper



    def to_dict(self) -> dict:
        """
        Return the underlying figure dictionary.

        Returns
        -------
        :class:`dict`
            The Plotly figure dictionary.
        """
        return self.fig
    

    def add_trace(self, channel: str) -> None:
        """
        Add a new set of traces to the figure for a given channel.

        This method creates three separate traces for the specified channel:

        - A primary trace for visible (unfiltered) points
        - A secondary trace for filtered (low-opacity) points
        - A third trace for the currently selected "big point"

        The traces are appended in order to the Plotly figure's data list.
        Styling and visibility behaviors are configured using the :class:`Trace` class,
        which responds to keys like `filtered`, `hidden`, and `big_point`.

        Parameters
        ----------
        channel : :class:`str`
            The name of the data channel to visualize (e.g., 'red', 'green', 'blue').

        """
        self.channels.append(channel)

        # Create 3 traces: regular, filtered, and big-point
        for _ in range(3):
            self.fig['data'].append(Trace(self.x_label, self.y_label, channel))

        # Configure filtered trace
        self.fig['data'][-2]['filtered'] = True
        self.fig['data'][-2]['showlegend'] = False

        # Configure big-point trace
        self.fig['data'][-1]['big_point'] = True
        self.fig['data'][-1]['showlegend'] = False
        self.fig['data'][-1]['marker']['size'] = 15
        self.fig['data'][-1]['marker']['line'] = {
            'width': 2,
            'color': 'DarkSlateGrey'
        }


    def filter_traces(self, channel: str) -> None:
        """
        Apply the current filter mask to all traces associated with a specific channel.

        This method updates the `x`, `y`, and `idx` values of traces in the figure
        based on whether they should be shown as filtered or not, using the
        `self.total_filter` boolean mask and the specified data channel.

        For "big point" traces, it toggles the `filtered` attribute depending on whether
        the corresponding index appears in the active subset. For other traces,
        it directly updates their data arrays with filtered or excluded values.

        Parameters
        ----------
        channel : :class:`str`
            The name of the data channel to apply filtering to. If 'gen' is passed,
            it will default to 'red' for trace alignment purposes.

        """
        if channel == 'gen':
            channel = 'red'

        # Extract data arrays
        x_data = np.array(self.all_data[self.x_label])
        y_data = np.array(self.all_data[self.y_label])
        idx_data = np.array(self.all_data['idx'])
        channel_filter = np.array(self.all_data['channel']) == channel

        # Determine which points are included/excluded by the total filter
        selected_data = np.logical_and(self.total_filter, channel_filter)
        filtered_out_data = np.logical_and(~self.total_filter, channel_filter)

        for i, img in enumerate(self.fig['data']):
            if img['channel'] != channel:
                continue

            if img['big_point']:
                if len(img['idx']) > 0:
                    if img['idx'][0] in idx_data[selected_data]:
                        self.fig['data'][i]['filtered'] = False
                    else:
                        self.fig['data'][i]['filtered'] = True
            else:
                # Update trace coordinates based on filter state
                if not img['filtered']:
                    self.fig['data'][i]['x'] = x_data[selected_data]
                    self.fig['data'][i]['y'] = y_data[selected_data]
                    self.fig['data'][i]['idx'] = idx_data[selected_data]
                else:
                    self.fig['data'][i]['x'] = x_data[filtered_out_data]
                    self.fig['data'][i]['y'] = y_data[filtered_out_data]
                    self.fig['data'][i]['idx'] = idx_data[filtered_out_data]


    def update_visibility(self, show_filtered_points: bool) -> None:
        """
        Update the visibility flag for filtered points.

        This method sets the internal flag controlling whether traces marked as
        `filtered` should be displayed or hidden in the plot. It does not directly
        modify the figure; you must call `apply_visibility()` afterward to apply the change.

        Parameters
        ----------
        show_filtered_points : bool
            If True, filtered points will be shown with reduced opacity.
            If False, filtered points will be hidden entirely.
        """
        self.show_filtered_points = show_filtered_points


    def apply_visibility(self) -> None:
        """
        Apply the current visibility setting to all filtered traces.

        This method updates the `'hidden'` property of each trace based on whether
        filtered points should be shown or hidden. It uses the internal flag
        `self.show_filtered_points`, which can be modified via `update_visibility()`.

        Traces with `filtered = True` will be:

        - Shown with reduced opacity if `show_filtered_points` is True
        - Fully hidden if `show_filtered_points` is False

        """
        if self.show_filtered_points:
            # Show filtered traces by un-hiding them
            for i, img in enumerate(self.fig['data']):
                if img['filtered']:
                    self.fig['data'][i]['hidden'] = False
        else:
            # Hide filtered traces completely
            for i, img in enumerate(self.fig['data']):
                if img['filtered']:
                    self.fig['data'][i]['hidden'] = True


    def update_channels(self, new_channels: list):
        """
        Add or remove traces to match a new list of active channels.

        Parameters
        ----------
        new_channels : :class:`list`
            The updated list of channels to be shown.

        Notes
        -----

        - Traces with 'channel' not in `new_channels` are removed.
        - Traces for new channels are added with default settings and shared data.

        """
        # Convert to sets for comparison
        old_set = set(self.channels)
        new_set = set(new_channels)

        to_remove = old_set - new_set
        to_add = new_set - old_set

        # Remove traces with now-unwanted channels
        self.fig['data'] = [trace for trace in self.fig['data'] if trace['channel'] not in to_remove]

        # Add traces for new channels
        if to_add:
            channel = next(iter(to_add))
            self.add_trace(channel)
            self.filter_traces(channel)
            self.plot_big_point()
            self.apply_visibility()

    

    def update_filters(self, active_filters: list[dict]) -> None:
        """
        Update the global filter mask based on the provided list of active filters.

        This method processes each filter definition and updates `self.total_filter`,
        a boolean mask indicating which data points should be retained. Filters may
        be simple threshold-based comparisons or special selection-based filters
        using image indices.

        Each filter is interpreted as either:

        - A selection filter: matches image indices (`label == "Selection ..."`)
        - A numeric filter: compares a field against a value using a specified operator
          from `env.OP`, with optional secondary filter logic.

        Parameters
        ----------
        active_filters : :class:`list` of :class:`dict`
            Each filter dict must include:

            - 'label' : :class:`str` — the field name or "Selection ...".
            - 'operator' : :class:`str` — key in `env.OP` for the comparison function.
            - 'value' : comparable — the value to compare against.

            Optionally:

            - 'secondary' : :class:`dict` — a nested filter with the same keys ('label', 'operator', 'value').

        Notes
        -----

        - All filters are combined using logical AND.
        - Secondary filters are combined with the primary using logical OR.
        - The resulting `self.total_filter` array is used by `filter_traces()` to control visibility.

        """
        filters = []

        for f in active_filters:
            # Handle selection-based filters (match by index)
            if f['label'].split()[0] == 'Selection':
                primary_filter = np.isin(self.all_data['idx'], f['value'])
                if f['operator'] == 'out':
                    primary_filter = ~primary_filter
                filters.append(primary_filter)

            else:
                # Handle threshold-style filters
                label_data = np.array(self.all_data[f['label']])
                value_type = type(self.all_data[f['label']][0])
                comparison_value = value_type(f['value'])
                primary_filter = env.OP[f['operator']](label_data, comparison_value)

                if 'secondary' in f:
                    secondary = f['secondary']
                    secondary_label_data = np.array(self.all_data[secondary['label']])
                    secondary_value_type = type(self.all_data[secondary['label']][0])
                    secondary_value = secondary_value_type(secondary['value'])
                    secondary_filter = env.OP[secondary['operator']](secondary_label_data, secondary_value)
                else:
                    # Use all-False secondary filter if not provided
                    secondary_filter = np.full(len(self.all_data['channel']), False)

                filters.append(np.logical_or(primary_filter, secondary_filter))

        # Combine all filters using logical AND
        for f in filters:
            self.total_filter = np.logical_and(self.total_filter, f)



    def gather_big_point(self, clickdata: dict) -> None:
        """
        Update the index of the selected "big point" based on click interaction data.

        This method extracts the index of the clicked point from Plotly's `clickData`
        dictionary and stores it in `self.big_point_idx`. This index is later used
        for highlighting or retrieving detailed information about the selected point.

        Parameters
        ----------
        clickdata : :class:`dict`
            A dictionary passed from a Dash Plotly `clickData` callback. It must contain
            a 'points' list with at least one item, each including:

            - 'curveNumber': int — the index of the clicked trace in `fig['data']`
            - 'pointIndex': int — the index of the clicked point within that trace

        """
        plot_index = clickdata['points'][0]['curveNumber']
        point_index = clickdata['points'][0]['pointIndex']
        self.big_point_idx = self.fig['data'][plot_index]['idx'][point_index]


    def plot_big_point(self) -> None:
        """
        Update the figure to highlight the currently selected "big point".

        This method sets the data for the special "big point" trace associated with
        each channel. It updates the trace with the coordinates of the selected point,
        based on `self.big_point_idx` and the current x/y axis labels.

        The point is only plotted if both its index and channel match a known data entry.
        Its `filtered` flag is also updated depending on whether the point passes the current filter.

        Returns
        -------
        None
            This method updates the figure in-place.
        
        Notes
        -----

        - The "gen" channel is treated as "red" for indexing purposes.

        """
        if self.big_point_idx is None:
            return

        big_point_selection = np.array(self.all_data['idx']) == self.big_point_idx

        for i, img in enumerate(self.fig['data']):
            if img['big_point']:
                channel = img['channel']
                if channel == 'gen':
                    channel = 'red'

                channel_filter = np.array(self.all_data['channel']) == channel
                selected_data_filter = np.logical_and(big_point_selection, channel_filter)

                self.fig['data'][i]['x'] = np.array(self.all_data[self.x_label])[selected_data_filter]
                self.fig['data'][i]['y'] = np.array(self.all_data[self.y_label])[selected_data_filter]
                self.fig['data'][i]['idx'] = np.array(self.all_data['idx'])[selected_data_filter]

                # Determine whether the selected point passes the current filters
                if np.logical_and(selected_data_filter, self.total_filter).any():
                    self.fig['data'][i]['filtered'] = False
                else:
                    self.fig['data'][i]['filtered'] = True



    def get_stats(self):
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

        data_figs = {img['channel']: img for img in self.fig['data'] if not img['filtered'] if not img['big_point']}

        stats_table = {}

        for axis,label in [['x', self.x_label],['y', self.y_label]]:
            stats_table[axis] = []
            try:
                if label in env.LABELS['gen']:
                    stats_table[axis].append({'label':label})
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
                                'label': f"{label}_{c}",
                                'value': f"{np.mean(data_figs[c][axis]):.2f} ± {np.std(data_figs[c][axis]):.2f}"
                            })
            except (ValueError, TypeError):
                stats_table[axis]=[]

        return stats_table


    def get_data_point_info(self) -> dict:
        """
        Retrieve detailed metadata for the currently selected "big point".

        This method gathers all relevant information for the data point indexed by
        `self.big_point_idx`, combining general metadata and channel-specific fit values
        into a single dictionary.

        General fields (from `env.LABELS['gen']`) are assumed to be identical across channels
        and are taken from the first matching index. Channel-specific fields (from `env.LABELS['fit']`)
        are extracted separately for each matching channel and labeled accordingly.

        Returns
        -------
        :class:`dict`
            A dictionary containing the values of all general and fit-related fields
            for the selected "big point". Fit values are keyed by `{label}_{channel}`.
        
        """
        indices = np.where(np.array(self.all_data['idx']) == self.big_point_idx)[0]

        out_dict = {}

        # General labels are channel-independent, so we use the first occurrence
        for label in env.LABELS['gen']:
            out_dict[label] = self.all_data[label][indices[0]]

        # Fit labels are channel-specific, so we include one per index
        for label in env.LABELS['fit']:
            for i in indices:
                channel = self.all_data['channel'][i]
                out_dict[f'{label}_{channel}'] = self.all_data[label][i]

        return out_dict



    def gonet_image(self, clickdata: dict) -> dict | None:
        """
        Retrieve and render a GONet image corresponding to the selected data point.

        This method locates the raw image file corresponding to the clicked data point
        and generates a Plotly-compatible figure dictionary for display in the dashboard.
        It overlays the image with a marker at the extraction center and a circular
        region representing the extraction aperture.

        Parameters
        ----------
        clickdata : :class:`dict`
            A Plotly click event dictionary from a Dash callback. Must contain:

            - 'points': list with at least one entry
            - 'curveNumber': index of the clicked trace
            - 'pointIndex': index of the clicked point within the trace

        Returns
        -------
        :class:`dict` or None
            A Plotly figure dictionary containing a heatmap of the selected image
            and overlay annotations. Returns None if the image cannot be loaded
            due to missing configuration or file.

        Notes
        -----

        - This function uses `env.GONET_IMAGES_PATH` to resolve image file paths.

        """
        if env.GONET_IMAGES_PATH is None:
            warnings.warn(
                "The environment variable for image paths is not set. Cannot display any image.",
                category=UserWarning
            )
        elif not env.GONET_IMAGES_PATH.exists():
            warnings.warn(
                f"The folder {env.GONET_IMAGES_PATH}, defined in the environment, does not exist.",
                category=UserWarning
            )
        else:
            plot_index = clickdata['points'][0]['curveNumber']
            channel = self.fig['data'][plot_index]['channel']

            # Identify the real index matching both the big point and the channel
            real_idx = np.argmax(
                np.logical_and(
                    np.array(self.all_data['idx']) == self.big_point_idx,
                    np.array(self.all_data['channel']) == channel
                )
            )

            filename = env.GONET_IMAGES_PATH / self.all_data['night'][real_idx] / "Horizontal" / self.all_data['filename'][real_idx]

            if not filename.exists():
                warnings.warn("Image not found at resolved path.", category=UserWarning)
                return

            # Load image data
            go = GONetFile.from_file(filename)

            outfig = {
                'data': [{
                    'z': go.channel(channel),
                    'type': 'heatmap'
                }],
                'layout': {
                    'showlegend': False,
                    'paper_bgcolor': env.BG_COLOR,
                    'plot_bgcolor': env.BG_COLOR,
                    'font': {'color': env.TEXT_COLOR},
                    'margin': {'l': 10, 'r': 10},
                    'xaxis': {'automargin': True, 'ticks': "outside", 'mirror': True},
                    'yaxis': {'automargin': True, 'ticks': "outside", 'mirror': True},
                }
            }
            del go

            # Center marker
            outfig['data'].append({
                'x': [self.all_data['center_x'][real_idx]],
                'y': [self.all_data['center_y'][real_idx]],
                'type': 'scatter',
                'mode': 'markers',
                'marker': {
                    'color': 'rgba(0, 0, 0, 1)',
                    'symbol': 'circle'
                }
            })

            # Circular aperture overlay
            c_x, c_y = [], []
            for ang in np.linspace(0, 2 * np.pi, 25):
                c_x.append(self.all_data['center_x'][real_idx] + self.all_data['extraction_radius'][real_idx] * np.cos(ang))
                c_y.append(self.all_data['center_y'][real_idx] + self.all_data['extraction_radius'][real_idx] * np.sin(ang))

            outfig['data'].append({
                'x': c_x,
                'y': c_y,
                'type': 'scatter',
                'mode': 'lines',
                'marker': {'color': 'rgba(0, 0, 0, 1)', 'symbol': 'circle'}
            })

            return outfig

        return None


# if 'range' in fig['layout']['xaxis']:
#     xaxis_range = fig['layout']['xaxis']['range']
#     yaxis_range = fig['layout']['yaxis']['range']
