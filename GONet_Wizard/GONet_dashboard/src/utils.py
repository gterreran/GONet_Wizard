"""
GONet Wizard Utility Functions.

This module provides reusable functions for plotting, filtering, statistical analysis,
and layout generation within the GONet Wizard dashboard application. These functions
support the construction of `Dash <https://dash.plotly.com/>`_ figures, dynamic filter UI elements, and filter logic
used in the callback system.

`Dash <https://dash.plotly.com/>`_ components from `dash` and `dash_daq` are used to construct UI elements dynamically.

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
import traceback, inspect, warnings, os
from functools import wraps

from dash import html, dcc, ctx, no_update
from dash.dependencies import Output, State
import dash_daq as daq

from GONet_Wizard.GONet_dashboard.src import env
from GONet_Wizard.GONet_dashboard.src.server import app

def debug_print(callback_fn):
    """
    Decorator that logs when a Dash callback is triggered, including the triggering component ID and source line.

    This decorator is useful for debugging and tracing which callbacks are being executed during development.
    Logging only occurs when the ``WERKZEUG_RUN_MAIN`` environment variable is set to "true", which ensures
    the message is printed only by the reloader's main process.

    Parameters
    ----------
    callback_fn : callable
        The Dash callback function to wrap.

    Returns
    -------
    callable
        The wrapped function that logs on invocation and then calls the original function.
    """
    @wraps(callback_fn)
    def wrapper(*args, **kwargs):
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            caller = inspect.stack()[1]
            print(f"{callback_fn.__name__} fired (line {caller.lineno}) triggered by {ctx.triggered_id}.")
        return callback_fn(*args, **kwargs)
    return wrapper


def gonet_callback(*args, **kwargs):
    """
    Custom Dash callback decorator that extends the original callback with automatic alert handling,
    debug logging, and error state protection.

    This decorator automatically appends three additional outputs for managing an alert container:

    - `alert-container.children` (message content)
    - `alert-container.className` (CSS class for styling)
    - `alert-container.style` (visibility/display logic)

    It also adds one hidden State:

    - `alert-container.className` (used to suppress execution if an error is already active)

    The wrapped callback will:
    - Suppress execution if the alert container is currently showing an error (`"alert-box error"`).
    - Capture and display any warnings issued during execution.
    - Catch exceptions and display a red alert box with the error message.
    - Log a message when the callback is triggered, including the triggering component (if `WERKZEUG_RUN_MAIN == "true"`).

    Parameters
    ----------
    *args : dash.Output, dash.Input, dash.State
        Positional arguments defining the Dash callback's outputs, inputs, and states.
        All initial Output(...) arguments are treated as actual user outputs.
    **kwargs : dict
        Additional keyword arguments passed to Dash's `app.callback`.

    Returns
    -------
    callable
        The decorated function registered as a Dash callback.
    """
    # Detect real outputs (all Output objects at the start of args)
    real_outputs = []
    for arg in args:
        if isinstance(arg, Output):
            real_outputs.append(arg)
        else:
            break
    n_real_outputs = len(real_outputs)

    # Add extra alert outputs
    alert_outputs = [
        Output("alert-container", "children", allow_duplicate=True),
        Output("alert-container", "className", allow_duplicate=True),
        Output("alert-container", "style", allow_duplicate=True),
    ]
    all_outputs = real_outputs + alert_outputs

    # Append hidden State to check alert status
    alert_state_input = State("alert-container", "className")

    def decorator(callback_fn):
        @wraps(callback_fn)
        def wrapped_fn(*fargs, **fkwargs):
            # Check for active error alert before proceeding
            alert_classname = fargs[-1]  # The last argument is the State
            if alert_classname == "alert-box error":
                return tuple([no_update] * (n_real_outputs + 3))

            try:
                if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
                    caller = inspect.stack()[1]
                    print(f"{callback_fn.__name__} fired (line {caller.lineno}) triggered by {ctx.triggered_id}.")

                # Capture warnings
                with warnings.catch_warnings(record=True) as wlist:
                    warnings.simplefilter("always")
                    result = callback_fn(*fargs[:-1], **fkwargs)  # Remove last arg (alert className)

                    # Ensure result is a tuple with the correct number of outputs
                    if n_real_outputs == 1:
                        result = (result,)  # wrap even lists as single output
                    elif not isinstance(result, (tuple, list)):
                        raise ValueError(
                            f"Callback must return {n_real_outputs} outputs, got a single value of type {type(result).__name__}"
                        )

                    if wlist:
                        msg = "; ".join(str(w.message) for w in wlist)
                        return (
                            *result,
                            f"⚠️ {msg}",
                            "alert-box warning",
                            {"display": "block"},
                        )

                return (*result, "", "", {"display": "none"})

            except Exception as e:
                print(f"Exception in callback: {callback_fn.__name__}")
                print(traceback.format_exc())
                return (
                    *[no_update] * n_real_outputs,
                    f"🚨 {str(e)}",
                    "alert-box error",
                    {"display": "block"},
                )

        # Register callback with appended State
        return app.callback(all_outputs, *args[n_real_outputs:], alert_state_input, **kwargs)(wrapped_fn)

    return decorator


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
                    dcc.Dropdown(className="custom-filter-operator", id={"type":'filter-operator', "index":idx}, options=list(env.OP.keys()), value = env.DEFAULT_OP),
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
        dcc.Dropdown(className="custom-filter-operator", id={"type":'second-filter-operator', "index":idx}, options=list(env.OP.keys()), value = env.DEFAULT_OP),
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