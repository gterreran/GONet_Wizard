"""
Defines the core interactivity for the GONet extraction GUI via Dash callbacks.

This module wires together user interactions with the UI elements defined in
`extract_layout.py`. It updates the displayed image, overlays shape-based masks,
computes extraction statistics, handles freehand drawing and path saving/loading,
and manages the state of shape-specific components. It also registers a
client-side callback for JSON downloads of the drawn region.

The shape-control logic is intentionally split into two callbacks: one callback
updates only the sidebar labels, placeholders, and visibility classes, while a
separate callback updates Plotly drawing mode and graph configuration. Keeping
these concerns separate makes the parameter controls react immediately when the
selected shape changes and avoids coupling simple UI label updates to figure
configuration changes.

**Functions**

- :func:`load_gonet_file`:
    Loads the GONet file for the selected file.

- :func:`store_binning`:
    Stores the binning information for the current extraction.

- :func:`update_figure_heatmap`:
    Update the heatmap figure based on the selected channel and binning option.

- :func:`update_shape_options`:
    Updates the visible sidebar controls, labels, placeholders, and CSS classes
    based on the selected extraction shape.

- :func:`update_shape_drawing_mode`:
    Updates the Plotly drag mode and drawing-toolbar configuration based on the
    selected extraction shape.

- :func:`catch_drawn_path`:
    Captures the path of a freehand-drawn region and updates the figure.

- :func:`activate_deactivate_freehand_buttons`:
    Enables or disables freehand drawing buttons based on the presence of a drawn path.

- :func:`update_extraction_params`:
    Updates extraction parameters based on user inputs and interactions.

- :func:`update_drawn_figure_and_extraction_values`:
    Draw the updated shape on the figure and display the extraction values.

- :func:`save_path`:
    Prepares the freehand path data for saving when the "Save Path" button is clicked.

- :func:`load_path`:
    Loads a previously saved freehand path from uploaded JSON content.

- :func:`update_extract_button_disabled`:
    Enables the interactive Extract button only after the selected shape is valid.

- :func:`extraction_button`:
    Validates extraction parameters, closes the setup window, and starts extraction.

- :func:`exit_app`:
    Requests closing the PyWebView window when the "Exit" button is clicked.

**Notes**

- Shapes supported: circle, rectangle, annulus, freehand.
- Statistics returned: total counts, mean, std dev, and number of selected pixels.

"""

import os
import json
from pathlib import Path
import logging
import threading
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dash import Input, Output, State, ctx, no_update
from dash_extensions.enrich import Serverside
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_utils.src.extractors.extraction_values import extract_counts_from_region
from GONet_Wizard.GONet_utils.src.extractors import extract_all
from GONet_Wizard.GONet_utils.src.extractors.core import extraction_output
from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import register_json_download, load_json
from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
from GONet_Wizard.GONet_utils.src.extract_app.extract_gui import (
    EXTRACT_GUI_WINDOW_KEY,
    cancel_interactive_extraction_if_unsubmitted,
    mark_interactive_extraction_submitted,
)
import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
from GONet_Wizard.GONet_utils.src.extract_app.extract_layout import files_path
from GONet_Wizard.logging_utils import PACKAGE_LOGGER_NAME
import numpy as np


def _package_info_logs_are_visible() -> bool:
    """
    Return whether package INFO logs are already visible to the caller.

    Returns
    -------
    bool
        ``True`` when the package logger is configured to show ``INFO`` records.
    """
    return logging.getLogger(PACKAGE_LOGGER_NAME).getEffectiveLevel() <= logging.INFO


def _print_output_path_if_needed(output_path: str) -> None:
    """
    Print the output path for plain CLI interactive runs when needed.

    The GUI terminal captures package ``INFO`` logs, so printing the same path
    there would duplicate feedback.  Plain CLI interactive runs usually hide
    ``INFO`` logs, so this helper prints the final path only in that case.

    Parameters
    ----------
    output_path : str
        Absolute path to the extraction output file.
    """
    if not _package_info_logs_are_visible():
        print(f"Results saved to {output_path}")


def _interactive_params_from_inputs(
    selected_shape,
    center_x,
    center_y,
    param1,
    param2,
    start_angle,
    end_angle,
    path,
):
    """
    Build an extraction-parameter dictionary from interactive form values.

    Parameters
    ----------
    selected_shape : str
        Current shape selector value.
    center_x, center_y : float or None
        Shape center coordinates from the interactive controls.
    param1, param2 : float or None
        Shape-specific parameters such as radius or side length.
    start_angle, end_angle : float or None
        Optional angular sector limits.
    path : str or None
        Freehand path data when using freehand extraction.

    Returns
    -------
    dict
        Extraction parameter dictionary compatible with ``Shape.from_dict``.
    """
    return {
        "shape": selected_shape,
        "x0": center_x,
        "y0": center_y,
        "param1": param1,
        "param2": param2,
        "start_angle": start_angle,
        "end_angle": end_angle,
        "path": path,
    }


@contextmanager
def _capture_terminal_stream(terminal_stream):
    """
    Forward interactive callback stdout, stderr, and package logs to a stream.

    Parameters
    ----------
    terminal_stream : object or None
        Stream bridge created by the launcher ``/run/stream`` endpoint.  When
        ``None``, output is left attached to the normal CLI process.

    Yields
    ------
    None
        Context in which callback output is redirected when a stream exists.
    """
    if terminal_stream is None:
        yield
        return

    package_logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    capture_handler = terminal_stream.logging_handler()

    previous_level = package_logger.level
    previous_handlers = list(package_logger.handlers)
    previous_propagate = package_logger.propagate
    effective_level = package_logger.getEffectiveLevel()
    if effective_level > logging.INFO:
        package_logger.setLevel(logging.INFO)

    package_logger.handlers = [capture_handler]
    package_logger.propagate = False
    try:
        with redirect_stdout(terminal_stream.stdout_writer()), redirect_stderr(terminal_stream.stderr_writer()):
            yield
    finally:
        package_logger.handlers = previous_handlers
        package_logger.propagate = previous_propagate
        package_logger.setLevel(previous_level)


def _clear_terminal_stream_if_current(terminal_stream) -> None:
    """
    Clear the configured terminal stream after it has been completed.

    Parameters
    ----------
    terminal_stream : object or None
        Stream bridge to clear only if it is still the active bridge.
    """
    if terminal_stream is not None and app.server.config.get("terminal_stream") is terminal_stream:
        app.server.config["terminal_stream"] = None


@app.callback(
    Output("gonet_file", "data"),
    Output("file-loaded", "children"),
    #---------------------
    Input("file-selector", "value"),
)
def load_gonet_file(selected_file):
    """
    Load the GONet file for the selected file.

    The GONet file is loaded server-side, for faster access.
    This callback runs automatically when the app loads. This ensures that the
    file is loaded properly and spawns all other necessary initializing
    callbacks.

    Parameters
    ----------
    selected_file : :class:`str`
        The name of the file selected in the file dropdown.

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`Serverside`: The loaded GONet as
          a :class:`~GONet_Wizard.GONet_utils.src.gonetfile.GONetFile` object.
        - :class:`str`: An empty string to update the `file-loaded` component,
          which serves as control for the loading state.

    """

    gof = GONetFile.from_file(os.path.join(files_path,selected_file))
    return Serverside(gof, key="gonet_file"), ''


@app.callback(
    Output("bin", "data"),
    #---------------------
    Input("binning-selector", "value"),
    #---------------------
    prevent_initial_call=True
)
def store_binning(binning):
    """
    Store the selected binning option as a more convenient :class:`int`.

    This callback stores the selected binning option in a `dcc.Store`
    component. The stored value can be used by other callbacks to adjust
    image processing based on the user's choice. The ``bin`` `dcc.Store`
    component is initialized in the layout, so it is available for use
    since the app starts.

    Parameters
    ----------
    binning : :class:`str`
        The binning option selected in the binning dropdown. Possible values are
        "1x1", "2x2", and "4x4".

    Returns
    -------
    :class:`int`
        The selected binning option to be stored in the `bin` store.

    """
    return int(binning[0])


@app.callback(
    Output("gonet-image", "figure"),
    Output("heatmap-ready-control", "children"),
    #---------------------
    Input("file-loaded", "children"),
    Input("channel-selector", "value"),
    Input("bin", "data"),
    #---------------------
    State("gonet_file", "data"),
    State("gonet-image", "figure"),
    #---------------------
    prevent_initial_call=True
)
def update_figure_heatmap(_, selected_channel, bin, gof, fig):
    """
    Update the heatmap figure based on the selected channel and binning option.

    This callback updates the `gonet-image` figure to display the image data
    corresponding to the selected channel and binning option. The image data
    is loaded using the :class:`~GONet_Wizard.GONet_utils.src.gonetfile.GONetFile`
    class, which extracts the specified channel from the selected file. When
    the figure is binned, the axis maintains the original unbinned pixel coordinates.
    Hovering over the figure will show the original pixel coordinates in the tooltip.

    To ensure the correct sequence of callbacks when the app loads for the first time,
    this callback waits on the `file-loaded` component to be updated before executing.

    Parameters
    ----------
    _ : :class:`str` or :class:`NoneType`
        Dummy Div triggered by :func:`.update_figure` when the figure is ready (ignored).
    selected_channel : :class:`str`
        The name of the channel selected in the channel dropdown. Possible values
        are "red", "green", and "blue".
    bin : :class:`int`
        The binning option selected in the binning dropdown. Possible values are
        1, 2, and 4.
    gof : :class:`~GONet_Wizard.GONet_utils.src.gonetfile.GONetFile`
        The GONet file currently loaded server-side.
    fig : :class:`dict`
        The current figure object for the `gonet-image` component, which is updated
        with the new image data.

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`dict`: The updated figure object with the new image data.
        - :class:`str`: An empty string to update the `heatmap-ready-control` component
          and signal that the figure update is complete.

    """

    data = gof.get_channel(selected_channel)
    # binning the data
    H, W = data.shape
    if bin > 1:
        # --- rebin (block mean) ---
        # Rebin: (H/bin, bin, W/bin, bin) → mean over inner axes (1,3)
        data = data.reshape(H // bin, bin, W // bin, bin).mean((1, 3))
        rows, cols = data.shape

        # Bin centers in original pixel coords
        x = (bin - 1) / 2 + bin * np.arange(cols)
        y = (bin - 1) / 2 + bin * np.arange(rows)

        # Customdata with original pixel coverage per bin
        x0 = (bin * np.arange(cols)).reshape(1, -1)
        y0 = (bin * np.arange(rows)).reshape(-1, 1)
        x1 = x0 + (bin - 1)
        y1 = y0 + (bin - 1)
        custom = np.stack([x0 + 0*y0, x1 + 0*y0, y0 + 0*x0, y1 + 0*x0], axis=-1)  # (rows, cols, 4)

        # --- Update main heatmap (trace 0) ---
        fig['data'][0].update({
            'type': 'heatmap',
            'x': x,
            'y': y,
            'zsmooth': False,
            'customdata': custom,
            'hovertemplate': (
                "center x=%{x:.1f}, y=%{y:.1f}<br>"
                "covers x=[%{customdata[0]}–%{customdata[1]}], "
                "y=[%{customdata[2]}–%{customdata[3]}]<br>"
                "val=%{z}<extra></extra>"
            ),
        })
    else:
        fig['data'][0].pop('customdata', None)
        fig['data'][0]['hovertemplate'] = (
            "center x=%{x:.1f}, y=%{y:.1f}<br>"
            "val=%{z}<extra></extra>"
        )
        fig['data'][0].pop('x', None)
        fig['data'][0].pop('y', None)

    fig['data'][0]['z'] = data.tolist()

    return fig, ''

@app.callback(
    Output("shape-options", "className"),
    Output("freehand-options", "className"),
    Output("shape-extra-parameters", "children"),
    Output("shape-parameter1", "placeholder"),
    Output("shape-parameter2-container", "className"),
    Output("shape-parameter2", "placeholder"),
    #---------------------
    Input("shape-selector", "value"),
)
def update_shape_options(selected_shape):
    """
    Update visible shape-specific controls when the selected shape changes.

    This callback is responsible only for the sidebar control state. It switches
    between the geometric-parameter panel and the freehand-drawing panel, updates
    the label for the shape-specific parameter row, and controls whether the
    second shape parameter is visible.

    The callback uses CSS class names rather than inline style dictionaries
    because the extraction GUI presentation is centralized in the shared static
    stylesheet. In particular, the second parameter is hidden by applying the
    ``hidden`` class to the parameter container, not to the input itself. This
    keeps both the layout and the callback aligned with the current styled
    extraction UI.

    Parameters
    ----------
    selected_shape : :class:`str`
        The extraction shape selected by the ``shape-selector`` radio items.
        Expected values are ``"circle"``, ``"rectangle"``, ``"annulus"``, and
        ``"freehand"``.

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`str`: CSS classes for the geometric shape-options panel.
        - :class:`str`: CSS classes for the freehand-options panel.
        - :class:`str`: Label text for the shape-specific parameter row.
        - :class:`str`: Placeholder text for the first shape parameter input.
        - :class:`str`: CSS classes for the second shape parameter container.
        - :class:`str`: Placeholder text for the second shape parameter input.

    Notes
    -----
    The visibility behavior is:

    - ``circle`` shows one parameter, interpreted as radius.
    - ``rectangle`` shows two parameters, interpreted as side lengths.
    - ``annulus`` shows two parameters, interpreted as inner and outer radius.
    - ``freehand`` hides the geometric parameter panel and shows the drawing
      controls instead.

    This callback is intentionally independent from
    :func:`update_shape_drawing_mode`, so that basic parameter-label updates do
    not depend on Plotly graph configuration updates.
    """

    if selected_shape == "freehand":
        output_shape_options = "extract-options-panel hidden"
        output_freehand_options = "extract-freehand-options"
    else:
        output_shape_options = "extract-options-panel"
        output_freehand_options = "extract-freehand-options hidden"

    if selected_shape == "circle":
        output_shape_extra_parameters = "Radius:"
        output_shape_parameter1_placeholder = "radius"
        output_shape_parameter2_container_class = "extract-half hidden"
        output_shape_parameter2_placeholder = ""

    elif selected_shape == "rectangle":
        output_shape_extra_parameters = "Side1, Side2:"
        output_shape_parameter1_placeholder = "side 1"
        output_shape_parameter2_container_class = "extract-half"
        output_shape_parameter2_placeholder = "side 2"

    elif selected_shape == "annulus":
        output_shape_extra_parameters = "Inner Radius, Outer Radius:"
        output_shape_parameter1_placeholder = "inner radius"
        output_shape_parameter2_container_class = "extract-half"
        output_shape_parameter2_placeholder = "outer radius"

    else:
        output_shape_extra_parameters = "Parameters"
        output_shape_parameter1_placeholder = ""
        output_shape_parameter2_container_class = "extract-half hidden"
        output_shape_parameter2_placeholder = ""

    return (
        output_shape_options,
        output_freehand_options,
        output_shape_extra_parameters,
        output_shape_parameter1_placeholder,
        output_shape_parameter2_container_class,
        output_shape_parameter2_placeholder,
    )


@app.callback(
    Output("extract-button", "disabled"),
    #---------------------
    Input("shape-selector", "value"),
    Input("shape-center-x", "value"),
    Input("shape-center-y", "value"),
    Input("shape-parameter1", "value"),
    Input("shape-parameter2", "value"),
    Input("shape-sector-start", "value"),
    Input("shape-sector-end", "value"),
    Input("drawn-path", "data"),
)
def update_extract_button_disabled(
    selected_shape,
    center_x,
    center_y,
    param1,
    param2,
    start_angle,
    end_angle,
    path,
):
    """
    Disable the Extract button until interactive parameters are valid.

    Parameters
    ----------
    selected_shape : str
        Current extraction shape selected in the interactive app.
    center_x, center_y : float or None
        Shape center coordinates.
    param1, param2 : float or None
        Shape-specific parameters.
    start_angle, end_angle : float or None
        Optional angular sector limits.
    path : str or None
        Freehand path data.

    Returns
    -------
    bool
        ``True`` when the button should be disabled, ``False`` when the
        parameters are complete enough to run extraction.
    """
    extraction_params = _interactive_params_from_inputs(
        selected_shape,
        center_x,
        center_y,
        param1,
        param2,
        start_angle,
        end_angle,
        path,
    )

    try:
        base.Shape.from_dict(extraction_params)
    except Exception:
        return True

    return False


@app.callback(
    Output("gonet-image", "figure", allow_duplicate=True),
    Output("gonet-image", "config"),
    Output("config-done-dummy-div", "children", allow_duplicate=True),
    #---------------------
    Input("heatmap-ready-control", "children"),
    Input("shape-selector", "value"),
    #---------------------
    State("gonet-image", "figure"),
    State("gonet-image", "config"),
    prevent_initial_call=True,
)
def update_shape_drawing_mode(_, selected_shape, fig, config):
    """
    Update Plotly drawing mode and graph configuration for the selected shape.

    This callback controls the interactive behavior of the image graph. For
    geometric shapes, the graph stays in normal zoom mode. For freehand
    extraction, the Plotly closed-path drawing tool is enabled and the graph
    drag mode is switched to ``"drawclosedpath"``.

    The callback also updates ``config-done-dummy-div`` as a synchronization
    signal for downstream extraction-parameter updates. This keeps parameter
    recomputation ordered after graph configuration changes when the app first
    loads or when the selected shape changes.

    Parameters
    ----------
    _ : :class:`str` or :data:`None`
        Dummy value from ``heatmap-ready-control``. The value itself is ignored;
        the input is used to ensure the image figure has been initialized before
        drawing-mode configuration is applied.
    selected_shape : :class:`str`
        The extraction shape selected by the ``shape-selector`` radio items.
        Expected values are ``"circle"``, ``"rectangle"``, ``"annulus"``, and
        ``"freehand"``.
    fig : :class:`dict` or :data:`None`
        Current Plotly figure dictionary for the ``gonet-image`` graph.
    config : :class:`dict` or :data:`None`
        Current Plotly graph configuration dictionary.

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`dict` or :data:`dash.no_update`: Updated Plotly figure, or
          :data:`dash.no_update` when the drag mode did not change.
        - :class:`dict` or :data:`dash.no_update`: Updated Plotly graph config,
          or :data:`dash.no_update` when the configuration did not change.
        - :class:`str`: Dummy synchronization value used by callbacks that
          recompute extraction parameters.

    Notes
    -----
    The callback avoids unnecessary graph updates when the requested drag mode
    is already active. This is especially useful when switching among geometric
    shapes, since circle, rectangle, and annulus all use Plotly zoom mode.
    """

    if fig is None:
        return no_update, no_update, selected_shape

    config = dict(config or {})
    layout = fig.setdefault("layout", {})
    previous_dragmode = layout.get("dragmode")

    if selected_shape == "freehand":
        config["modeBarButtonsToAdd"] = ["drawclosedpath"]
        layout["dragmode"] = "drawclosedpath"
    else:
        config["modeBarButtonsToAdd"] = []
        layout["dragmode"] = "zoom"

    if previous_dragmode == layout["dragmode"]:
        fig = no_update
        config = no_update

    return fig, config, ''


@app.callback(
    Output("drawn-path", "data"),
    Output("gonet-image", "figure", allow_duplicate=True),
    #---------------------
    Input("gonet-image", "relayoutData"),
    Input("freehand-reset-button", "n_clicks"),
    #---------------------
    State("gonet-image", "figure"),
    #---------------------
    prevent_initial_call=True
)
def catch_drawn_path(relayout_data, reset_button, fig):
    """
    Capture the path of a freehand-drawn region and update the figure.

    This callback listens for changes in the `relayoutData` property of the `gonet-image`
    figure, which contains information about shapes drawn by the user. It captures the
    path of the most recently drawn shape and updates the figure layout accordingly.
    If the "Reset" button is clicked, all drawn shapes are cleared.

    Parameters
    ----------
    relayout_data : :class:`dict` or :data:`NoneType`
        Data from the `relayoutData` property of the `gonet-image` figure, containing
        information about drawn shapes. This includes the `path` key for freehand-drawn
        regions.
    reset_button : :class:`int` or :data:`NoneType`
        Click count of the "Reset" button for freehand drawing. Used to determine if
        the user has requested to clear all drawn shapes.
    fig : :class:`dict`
        The current figure object for the `gonet-image` component, which is updated
        with the new shape or cleared shapes.

    Returns
    -------
    tuple
        A tuple containing:
        
        - :class:`str` or :data:`NoneType`: The path of the most recently drawn shape,
          or `None` if the shapes are cleared.
        - :class:`dict`: The updated figure object with the new shape or cleared shapes.

    """

    if ctx.triggered_id == "freehand-reset-button":
        fig.setdefault("layout", {}).pop("shapes", None)
        if len(fig.get("data", [])) > 1:
            fig["data"][1]['z'] = []
        return None, fig

    if relayout_data is None:
        return no_update, no_update

    if 'shapes' in relayout_data:
        if len(fig['layout']['shapes']) > 1:
            fig['layout']['shapes'].pop(0)
        return relayout_data['shapes'][-1]['path'], fig
    elif 'shapes[0].path' in relayout_data:
        return relayout_data['shapes[0].path'], no_update
    else:
        return no_update, no_update


@app.callback(
    Output("freehand-reset-button", "disabled"),
    Output("freehand-save-button", "disabled"),
    #---------------------
    Input("drawn-path", "data"),
    #---------------------
    prevent_initial_call=True
)
def activate_deactivate_freehand_buttons(path):
    """
    Enable or disable freehand drawing buttons based on the presence of a drawn path.

    This callback controls the state of the "Reset" and "Save" buttons for freehand
    drawing. If a path is present in the `drawn-path` store, the buttons are enabled.
    Otherwise, they remain disabled.

    Parameters
    ----------
    path : :class:`str` or :data:`NoneType`
        The current freehand path data stored in the `drawn-path` store. If `None`,
        no path is present, and the buttons will be disabled.

    Returns
    -------
    tuple
        A tuple containing:
        - :class:`bool`: Whether the "Reset" button should be disabled.
        - :class:`bool`: Whether the "Save" button should be disabled.

    Notes
    -----
    - The "Reset" button clears the current freehand path when clicked.
    - The "Save" button allows the user to save the current freehand path to a file.
    - Both buttons are disabled when no path is present.

    """

    if path is not None:
        output_freehand_reset_button_disabled = False
        output_freehand_save_button_disabled = False
    else:
        output_freehand_reset_button_disabled = True
        output_freehand_save_button_disabled = True
    
    return output_freehand_reset_button_disabled, output_freehand_save_button_disabled


@app.callback(
    Output("extraction-params", "data", allow_duplicate=True),
    Output("mask", "data"),
    Output("extracted-values", "data"),
    Output("error-banner", "children"),
    Output("error-banner", "className"),
    #---------------------
    Input("config-done-dummy-div", "children"),
    Input("shape-center-x", "value"),
    Input("shape-center-y", "value"),
    Input("shape-parameter1", "value"),
    Input("shape-parameter2", "value"),
    Input("shape-sector-start", "value"),
    Input("shape-sector-end", "value"),
    Input("drawn-path", "data"),
    #---------------------
    State("shape-selector", "value"),
    State("gonet_file", "data"),
    State("channel-selector", "value"),
    State("mask", "data"),
    State("error-banner", "className"),
    prevent_initial_call=True
)
def update_extraction_params(_, center_x, center_y, param1, param2, start_angle, end_angle, path, selected_shape, gof, channel, masked_figure, error_banner_class):
    """
    Update extraction parameters based on user inputs.

    This callback updates the `extraction-params` store with the current values
    of the shape parameters entered by the user or with the latest freehand path.
    The updated extraction parameters
    are then used to generate the mask for the selected shape, which is stored
    in the `mask` component. Using this mask, the extracted values are computed
    and stored in the `extracted-values` component.

    This callback also handles any errors that may occur with invalid parameters,
    by displaying an error message in the `error-banner` component. The error
    message will be displayed only once all the parameters have been validated,
    and not for every single parameter input.

    Parameters
    ----------
    _ : :class:`str` or :data:`NoneType`
        The value of the `config-done-dummy-div` component, which indicates when the
        figure configuration is complete. This guarantees that the figure's configuration
        is fully updated before any subsequent extraction gets triggered by the
        `extraction-params` component.
    center_x : :class:`float` or :data:`NoneType`
        X-coordinate of the shape center (if applicable).
    center_y : :class:`float` or :data:`NoneType`
        Y-coordinate of the shape center (if applicable).
    param1 : :class:`float` or :data:`NoneType`
        First shape-specific parameter (e.g., radius, side length, inner radius).
    param2 : :class:`float` or :data:`NoneType`
        Second shape-specific parameter (e.g., side length, outer radius).
    start_angle : :class:`float` or :data:`NoneType`
        Start angle for sector shapes (in degrees).
    end_angle : :class:`float` or :data:`NoneType`
        End angle for sector shapes (in degrees).
    selected_shape : :class:`str`
        The currently selected shape type from the dropdown. Possible values are
        "circle", "rectangle", "annulus", and "freehand".
    path : :class:`str` or :data:`NoneType`
        The current freehand path data stored in the `drawn-path` store.
    gof : :class:`~GONet_Wizard.GONet_utils.src.gonetfile.GONetFile`
        The GONet file currently loaded server-side.
    channel : :class:`str`
        The currently selected channel from the `channel-selector` component.
    masked_figure : :class:`list`
        The current masked figure data stored in the `mask` store.
    error_banner_class : :class:`str`
        The current CSS classes for the error banner.

    Returns
    -------
    tuple
        A tuple containing:
        
        - :class:`dict` with updated extraction parameters.
        - :class:`list` with the updated masked figure data.
        - :class:`Serverside` the :class:`~GONet_Wizard.GONet_utils.src.extract_app.extractors.extraction_output`
          object with the extracted values.
        - :class:`str` with any error messages for the banner.
        - :class:`str` with the updated visibility class for the error banner.

    """

    error_banner_children = ''
    error_banner_class = "extract-error-banner"

    extraction_params = _interactive_params_from_inputs(
        selected_shape,
        center_x,
        center_y,
        param1,
        param2,
        start_angle,
        end_angle,
        path,
    )

    masked_figure_initial = list(masked_figure or [])

    data = gof.get_channel(channel)

    try:
        shape = base.Shape.from_dict(extraction_params)
    except base.IncompleteShapeError:
        output = extraction_output(0, 0, 0, 0)
        masked_figure = []
    except (ValueError, TypeError) as e:
        error_banner_class = "extract-error-banner is-visible"
        return no_update, no_update, no_update, str(e), error_banner_class
    else:
        mask = shape.mask(data)
        masked_figure = np.where(mask, 1, np.nan)
        masked_figure = masked_figure.tolist()
        output = extract_counts_from_region(data, mask)
        

    if masked_figure_initial != masked_figure:
        return extraction_params, masked_figure, Serverside(output, key="extraction_output"), error_banner_children, error_banner_class
    else:
        return no_update, no_update, no_update, error_banner_children, error_banner_class


@app.callback(
    Output("gonet-image", "figure", allow_duplicate=True),
    Output("stat-total", "children"),
    Output("stat-mean", "children"),
    Output("stat-std", "children"),
    Output("stat-npix", "children"),
    #---------------------
    Input("extraction-params", "data"),
    #---------------------
    State("gonet-image", "figure"),
    State("mask", "data"),
    State("extracted-values", "data"),
    #---------------------
    prevent_initial_call=True
)
def update_drawn_figure_and_extraction_values(extraction_params, fig, mask, extracted_values):
    """
    Draw the updated shape on the figure and display the extraction values.

    This callback draws the new shape and display the pixel statistics (total counts,
    mean, standard deviation, and pixel count) for the region defined by the current
    extraction parameters and the drawn path. 

    Parameters
    ----------
    extraction_params : :class:`dict`
        The current extraction parameters stored in the `extraction-params` store.
        This includes the shape type, center coordinates, dimensions, angles, and
        the drawn path (if applicable).
    fig : :class:`dict`
        The current figure object for the `gonet-image` component, which contains
        the image data used for the extraction.
    mask : :class:`list`
        The current mask data stored in the ``mask`` store.
    extracted_values : :class:`~GONet_Wizard.GONet_utils.src.extractors.core.ExtractionOutput`
        Object containing the extracted values.
    

    Returns
    -------
    tuple
        A tuple containing:
        - :class:`dict`: The updated figure object for the `gonet-image` component.
        - :class:`int`: Total pixel counts within the selected region.
        - :class:`float`: Mean pixel value within the selected region.
        - :class:`float`: Standard deviation of pixel values within the selected region.
        - :class:`int`: Number of pixels within the selected region.

    """ 

    if extracted_values is None:
        extracted_values = extraction_output(0, 0, 0, 0)

    try:
        shape = base.Shape.from_dict(extraction_params)
    except base.IncompleteShapeError:
        fig.setdefault("layout", {}).pop("shapes", None)
        if len(fig.get("data", [])) > 1:
            fig["data"][1]['z'] = []
    else:
        fig.setdefault("layout", {})["shapes"] = shape.draw()
        if len(fig.get("data", [])) > 1:
            fig["data"][1]['z'] = mask

    return fig, f"{extracted_values.total_counts}", f"{extracted_values.mean_counts:.2f}", f"{extracted_values.std:.2f}", f"{extracted_values.npixels}"


# Registering client-side callback handling the download
register_json_download(
    app,
    Output("dummy-div", "children"),
    Input("save-path", "data")
)


@app.callback(
    Output("save-path", "data"),
    #---------------------
    Input("freehand-save-button", 'n_clicks'),
    #---------------------
    State("drawn-path", "data"),
    #---------------------
    prevent_initial_call=True
)
def save_path(_, path):
    """
    Callback to prepare the freehand path data for saving.

    This function is triggered when the "Save Path" button is clicked.
    It returns the currently drawn path so that it can be serialized and downloaded
    via a client-side callback.

    Parameters
    ----------
    _ : :class:`int` or :class:`NoneType`
        Click count of the "Save Path" button (ignored).

    path : :class:`str` or :data:`NoneType`
        The path of the freehand-drawn region, if applicable. If `None`, no freehand
        region is used.

    Returns
    -------
    :class:`list`
        The same `path` object, to be passed to the `save-path` store for download.
    """

    return path


@app.callback(
    Output("config-done-dummy-div", "children", allow_duplicate=True),
    Output("drawn-path", "data", allow_duplicate=True),
    #---------------------
    Input("upload-path", 'contents'),
    #---------------------
    prevent_initial_call=True
)
def load_path(contents):
    """
    Load a previously saved freehand path from uploaded JSON content.

    This callback is triggered when the user uploads a JSON file via the upload
    component. The uploaded file is parsed, and the freehand path data is loaded
    into the `drawn-path` store. The extraction parameters are updated to include
    the loaded path.

    Parameters
    ----------
    contents : :class:`str`
        Base64-encoded contents of the uploaded JSON file, as returned by
        Dash's `dcc.Upload` component. The file must contain valid JSON data
        representing the freehand path.

    Returns
    -------
    tuple
        A tuple containing:
        
        - :class:`dict`: Updated extraction parameters with the loaded path.
        - :class:`str`: An empty string to update the `config-done-dummy-div` component,
          which serves as control for the extraction-params component.

    """

    return '', load_json(contents)



def _write_interactive_extraction_output(extraction_params):
    """
    Run the selected interactive extraction and write the output file.

    Parameters
    ----------
    extraction_params : dict
        Validated extraction parameters selected in the interactive window.

    Returns
    -------
    str
        Absolute path to the written JSON or CSV output file.

    Notes
    -----
    The integrated extraction GUI is launched asynchronously by the shared UI
    runtime.  The Extract button therefore starts the extraction after the
    selection window has been dismissed, while progress is reported either to
    the main GUI terminal stream or to the normal CLI terminal.
    """
    from GONet_Wizard.commands.extract import validate_output_file

    files = app.server.config.get("data_files") or []
    channels = app.server.config.get("channels") or ["red", "green", "blue"]
    output = app.server.config.get("output")
    output_type = app.server.config.get("output_type")

    shape = extraction_params.get("shape")
    if output is None:
        if output_type is None:
            output_type = "json"
        output = f"extraction_{shape}.{output_type}"

    output, output_type = validate_output_file(output, output_type)
    out_epoch_list = extract_all(files, channels, extraction_params)

    if output_type == "csv":
        import pandas as pd

        df = pd.json_normalize(out_epoch_list, sep="_")
        df.to_csv(output, index=False)
    else:
        with open(output, "w") as f:
            json.dump(out_epoch_list, f, indent=4)

    output_path = str(Path(output).resolve())
    logging.getLogger(PACKAGE_LOGGER_NAME).info("Results saved to %s", output_path)
    _print_output_path_if_needed(output_path)
    return output_path


def _run_interactive_extraction_in_background(extraction_params, terminal_stream):
    """
    Run selected interactive extraction after closing the setup window.

    Parameters
    ----------
    extraction_params : dict
        Validated extraction parameters selected by the user.
    terminal_stream : object or None
        Optional stream bridge for the launcher terminal panel.  When ``None``,
        the thread is used by a CLI launch and the process waits for completion.
    """
    try:
        with _capture_terminal_stream(terminal_stream):
            output = _write_interactive_extraction_output(extraction_params)
    except Exception as e:
        if terminal_stream is not None:
            terminal_stream.finish(
                status="error",
                message=f"Interactive extraction failed: {e}",
                traceback_text="".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                ),
            )
            _clear_terminal_stream_if_current(terminal_stream)
        return

    app.server.config["extraction_params"] = extraction_params
    app.server.config["last_output"] = output
    if terminal_stream is not None:
        terminal_stream.finish(
            status="success",
            message="Interactive extraction finished.",
            output=str(output),
        )
        _clear_terminal_stream_if_current(terminal_stream)


@app.callback(
    Output("exit-button", "n_clicks"),
    Output("error-banner", "children", allow_duplicate=True),
    Output("error-banner", "className", allow_duplicate=True),
    #---------------------
    Input("extract-button", "n_clicks"),
    #---------------------
    State("extraction-params", "data"),
    State("drawn-path", "data"),
    State("shape-selector", "value"),
    State("exit-button", "n_clicks"),
    #---------------------
    prevent_initial_call=True
)
def extraction_button(_, extraction_params, path, selected_shape, n):
    """
    Validate parameters, close the setup window, and start extraction.

    This callback is triggered when the user clicks the "Extract" button in the
    interactive extraction window.  It validates the current parameters before
    closing the window, starts the extraction in a worker thread, and lets the
    main GUI terminal stream or CLI terminal report progress and completion.

    Parameters
    ----------
    _ : :class:`int` or :data:`None`
        The number of times the "Extract" button has been clicked.
        This parameter is unused but required by Dash as the input trigger.
    extraction_params : :class:`dict`
        The extraction parameters retrieved from the ``extraction-params``
        `dcc.Store` component in the Dash layout.
    path : :class:`str` or :data:`NoneType`
        The path of the freehand-drawn region, if applicable. If `None`, no freehand
        region is used.
    selected_shape : :class:`str`
        Current value of the shape selector. Used to keep freehand extraction
        parameters synchronized with the drawn path.
    n : :class:`int` or :data:`None`
        The current number of clicks on the "Exit" button.

    Returns
    -------
    tuple
        A tuple containing the exit-click update and error-banner contents/classes.
        On success, the setup window closes immediately while extraction
        continues.  On failure, the window remains open and the error banner
        reports the validation error.
    """

    extraction_params = dict(extraction_params or {})

    # The path store is the authoritative source for freehand geometry.  Use
    # the current shape selector as a guard against a stale extraction-params
    # store when the user clicks Extract immediately after drawing.
    if selected_shape == "freehand":
        extraction_params["shape"] = "freehand"
        extraction_params["path"] = path
    else:
        extraction_params["path"] = path

    terminal_stream = app.server.config.get("terminal_stream")

    try:
        # Validate the shape before closing the setup window.  This keeps the
        # user in the interactive form when parameters are incomplete or invalid,
        # but allows the actual extraction to continue after the window closes.
        base.Shape.from_dict(extraction_params)
    except Exception as e:
        if terminal_stream is not None:
            terminal_stream.finish(
                status="error",
                message=f"Interactive extraction failed: {e}",
                traceback_text="".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                ),
            )
            _clear_terminal_stream_if_current(terminal_stream)
        return no_update, f"Extraction failed: {e}", "extract-error-banner is-visible"

    mark_interactive_extraction_submitted()

    if terminal_stream is not None:
        terminal_stream.append(
            "Interactive extraction submitted. Closing setup window; "
            "progress will continue here.\n"
        )

    worker = threading.Thread(
        target=_run_interactive_extraction_in_background,
        args=(extraction_params, terminal_stream),
        # Plain CLI launches do not have a main GUI terminal stream.  Keep the
        # worker non-daemonic in that mode so the Python process waits for the
        # extraction to finish after the setup window closes.
        daemon=terminal_stream is not None,
    )
    worker.start()

    from GONet_Wizard.ui import WINDOWS
    WINDOWS.close(EXTRACT_GUI_WINDOW_KEY)
    return no_update, "", "extract-error-banner"


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
    cancel_interactive_extraction_if_unsubmitted()

    from GONet_Wizard.ui import WINDOWS
    WINDOWS.close(EXTRACT_GUI_WINDOW_KEY)
    return True
