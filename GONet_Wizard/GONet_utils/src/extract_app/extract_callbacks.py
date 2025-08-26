"""
Defines the core interactivity for the GONet extraction GUI via Dash callbacks.

This module wires together user interactions with the UI elements defined in
`extract_layout.py`. It updates the displayed image, overlays shape-based masks,
computes extraction statistics, handles freehand drawing and path saving/loading,
and manages the state of shape-specific components. It also registers a
client-side callback for JSON downloads of the drawn region.

**Functions**

- :func:`update_figure`:
    Updates the displayed image based on the selected file and channel.

- :func:`update_shape_options`:
    Adjusts visibility and labels of shape-specific input fields based on the selected shape.

- :func:`catch_drawn_path`:
    Captures the path of a freehand-drawn region and updates the figure.

- :func:`activate_deactivate_freehand_buttons`:
    Enables or disables freehand drawing buttons based on the presence of a drawn path.

- :func:`update_extraction_params`:
    Updates extraction parameters based on user inputs and interactions.

- :func:`update_extraction_values`:
    Computes extraction statistics (total, mean, std dev, and pixel count) for the selected region.

- :func:`update_drawn_shapes`:
    Updates the figure with drawn shapes based on the selected shape and extraction parameters.

- :func:`save_path`:
    Prepares the freehand path data for saving when the "Save Path" button is clicked.

- :func:`load_path`:
    Loads a previously saved freehand path from uploaded JSON content.

- :func:`extraction_button`:
    Stores extraction parameters and programmatically triggers the "Exit" button.

- :func:`exit_app`:
    Requests closing the PyWebView window when the "Exit" button is clicked.

**Notes**

- Shapes supported: circle, rectangle, annulus, freehand.
- Statistics returned: total counts, mean, std dev, and number of selected pixels.

"""

import os
from dash import Input, Output, State, ctx, no_update
from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from GONet_Wizard.GONet_utils.src.extractors import extract_counts_from_region
from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import register_json_download, load_json
from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
from GONet_Wizard.GONet_utils.src.extract_app.extract_layout import files_path


@app.callback(
    Output("gonet-image", "figure"),
    Output("ready-dummy-div", "children"),
    #---------------------
    Input("file-selector", "value"),
    Input("channel-selector", "value"),
    #---------------------
    State("gonet-image", "figure"),
)
def update_figure(selected_file, selected_channel, fig):
    """
    Update the displayed image based on the selected file and channel.

    This callback updates the `gonet-image` figure to display the image data
    corresponding to the selected file and channel. The image data is loaded
    from the specified file, and the selected channel (e.g., "red", "green",
    "blue") is extracted and displayed in the figure.

    This is the only callback in the module without `prevent_initial_call=True`,
    meaning it runs automatically when the app loads. This ensures that the
    figure is initialized properly and spawns all other necessary initializing
    callbacks.

    Parameters
    ----------
    selected_file : :class:`str`
        The name of the file selected in the file dropdown.
    selected_channel : :class:`str`
        The name of the channel selected in the channel dropdown. Possible values
        are "red", "green", and "blue".
    fig : :class:`dict`
        The current figure object for the `gonet-image` component, which is updated
        with the new image data.

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`dict`: The updated figure object with the new image data.
        - :class:`str`: An empty string to update the `ready-dummy-div` component
          and signal that the figure update is complete.

    Notes
    -----
    - The image data is loaded using the :class:`GONetFile` class, which extracts
      the specified channel from the selected file.

    """

    gof = GONetFile.from_file(os.path.join(files_path,selected_file))
    fig['data'][0]['z'] = gof.get_channel(selected_channel)
    del gof

    return fig, ''


@app.callback(
    Output("shape-options", "style"),
    Output("freehand-options", "style"),
    Output("shape-extra-parameters", "children"),
    Output("shape-parameter1", "placeholder"),
    Output("shape-parameter2", "style"),
    Output("shape-parameter2", "placeholder"),
    Output("extraction-params", "data"),
    #---------------------
    Input("ready-dummy-div", "children"),
    Input("shape-selector", "value"),
    #---------------------
    State("extraction-params", "data"),
    #---------------------
    prevent_initial_call=True
)
def update_shape_options(_, selected_shape, current_params):
    """
    Update visibility and labels of shape-specific input fields based on selected shape.

    This callback adjusts the visibility of input fields and buttons related to
    shape parameters depending on the user's selection in the shape dropdown.
    It ensures that only relevant inputs are shown for the chosen shape type.
    Is also updates the ``shape`` key in the `extraction-params` store
    to reflect the current selection.

    To guarantee the correct sequence of callbacks, this callback waits on the
    :func:`.update_figure` callback to complete before executing, by listening to
    changes to the `ready-dummy-div` component.

    Parameters
    ----------
    _ : :class:`str` or :class:`NoneType`
        Dummy Div triggered by :func:`.update_figure` when the figure is ready (ignored).

    selected_shape : :class:`str`
        The currently selected shape type from the dropdown. Possible values are
        "circle", "rectangle", "annulus", and "freehand".
    
    current_params : :class:`dict`
        The current extraction parameters stored in the `extraction-params` store.
        This is used to update the state of the parameters based on the selected shape.

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`dict`: CSS style for the shape options container (to show/hide it).
        - :class:`dict`: CSS style for the freehand options container (to show/hide it).
        - :class:`str` or :data:`dash.no_update`: Label text for extra parameters.
        - :class:`str` or :data:`dash.no_update`: Placeholder text for parameter 1 input.
        - :class:`dict` or :data:`dash.no_update`: CSS style for parameter 2 input (to show/hide it).
        - :class:`str` or :data:`dash.no_update`: Placeholder text for parameter 2 input.
        - :class:`dict`: Updated extraction parameters to be stored in the `extraction-params` store.

    """

    output_shape_extra_parameters = no_update
    output_shape_parameter1_placeholder = no_update
    output_shape_parameter2_style = no_update
    output_shape_parameter2_placeholder = no_update

    if selected_shape == "freehand":
        output_shape_options = {"display": "none"}
        output_freehand_options = {"display": "block"}
    else:
        output_shape_options = {"display": "block"}
        output_freehand_options = {"display": "none"}
    
    if selected_shape == "circle":
        output_shape_extra_parameters = "Radius:"
        output_shape_parameter1_placeholder = "radius"
        output_shape_parameter2_style = {"display": "none"}
    elif selected_shape == "rectangle":
        output_shape_extra_parameters = "Side1, Side2:"
        output_shape_parameter1_placeholder = "side 1"
        output_shape_parameter2_placeholder = "side 2"
        output_shape_parameter2_style = {"display": "block", "width": "100%"}
    elif selected_shape == "annulus":
        output_shape_extra_parameters = "Inner Radius, Outer Radius:"
        output_shape_parameter1_placeholder = "inner radius"
        output_shape_parameter2_placeholder = "outer radius"
        output_shape_parameter2_style = {"display": "block", "width": "100%"}

    current_params['shape'] = selected_shape

    return output_shape_options, output_freehand_options, output_shape_extra_parameters, output_shape_parameter1_placeholder, output_shape_parameter2_style, output_shape_parameter2_placeholder, current_params


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
        del fig["layout"]['shapes']
        return None, fig
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
    #---------------------
    Input("shape-center-x", "value"),
    Input("shape-center-y", "value"),
    Input("shape-parameter1", "value"),
    Input("shape-parameter2", "value"),
    Input("shape-sector-start", "value"),
    Input("shape-sector-end", "value"),
    #---------------------
    State("extraction-params", "data"),
    prevent_initial_call=True
)
def update_extraction_params(center_x, center_y, param1, param2, start_angle, end_angle, current_params):
    """
    Update extraction parameters based on user inputs.

    This callback updates the `extraction-params` store with the current values
    of the shape parameters entered by the user. It ensures that the latest
    values for the shape's center, dimensions, and angles are stored for use
    during the extraction process.

    Parameters
    ----------
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
    current_params : :class:`dict`
        Current extraction parameters stored in the `extraction-params` store.

    Returns
    -------
    :class:`dict`
        Updated extraction parameters to be stored in the `extraction-params` store.

    Notes
    -----
    - The `shape` key in `current_params` remains unchanged.

    """

    return {'shape': current_params['shape'], 'x0': center_x, 'y0': center_y, 'param1': param1, 'param2': param2, 'start_angle': start_angle, 'end_angle': end_angle}


@app.callback(
    Output("stat-total", "children"),
    Output("stat-mean", "children"),
    Output("stat-std", "children"),
    Output("stat-npix", "children"),
    #---------------------
    Input("extraction-params", "data"),
    Input("drawn-path", "data"),
    #---------------------
    State("gonet-image", "figure"),
    prevent_initial_call=True
)
def update_extraction_values(extraction_params, path, fig):
    """
    Compute and update extraction statistics for the selected region.

    This callback calculates pixel statistics (total counts, mean, standard deviation,
    and pixel count) for the region defined by the current extraction parameters and
    the drawn path. The results are displayed in the corresponding statistic fields.

    Parameters
    ----------
    extraction_params : :class:`dict`
        The current extraction parameters stored in the `extraction-params` store.
        This includes the shape type, center coordinates, dimensions, angles, and
        the drawn path (if applicable).
    path : :class:`str` or :data:`NoneType`
        The path of the freehand-drawn region, if applicable. If `None`, no freehand
        region is used.
    fig : :class:`dict`
        The current figure object for the `gonet-image` component, which contains
        the image data used for the extraction.

    Returns
    -------
    tuple
        A tuple containing:
        - :class:`float` or :class:`str`: Total pixel counts within the selected region.
        - :class:`float` or :class:`str`: Mean pixel value within the selected region.
        - :class:`float` or :class:`str`: Standard deviation of pixel values within the selected region.
        - :class:`int` or :class:`str`: Number of pixels within the selected region.

    Notes
    -----
    - If the extraction parameters are incomplete (e.g., missing shape dimensions),
      the statistics are not computed, and empty strings are returned.
    - The :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class is used to generate a mask for the selected region based on
      the extraction parameters.
    - The results of the extraction are parsed from a :class:`~GONet_Wizard.GONet_utils.src.extract_app.extractors.extraction_output` class.

    """

    extraction_params['path'] = path
    try:
        shape = base.Shape.from_dict(extraction_params)
    except base.IncompleteShapeError:
        output_stat_total = ""
        output_stat_mean = ""
        output_stat_std = ""
        output_stat_npix = ""
    else:
        mask = shape.mask(fig['data'][0]['z'])
        output = extract_counts_from_region(fig['data'][0]['z'], mask)
        output_stat_total = output.total_counts
        output_stat_mean = output.mean_counts
        output_stat_std = output.std
        output_stat_npix = output.npixels
    
    return output_stat_total, output_stat_mean, output_stat_std, output_stat_npix


@app.callback(
    Output("gonet-image", "figure", allow_duplicate=True),
    Output("gonet-image", "config"),
    #---------------------
    Input("extraction-params", "data"),
    #---------------------
    State("gonet-image", "figure"),
    State("gonet-image", "config"),
    State("shape-selector", "value"),
    State("drawn-path", "data"),
    #---------------------
    prevent_initial_call=True   
)
def update_drawn_shapes(extraction_params, fig, config, selected_shape, path):
    """
    Update the figure with drawn shapes based on the selected shape and extraction parameters.

    This callback updates the `gonet-image` figure to display the shape defined by the
    current extraction parameters. It adjusts the figure's layout and configuration
    based on the selected shape type (e.g., circle, rectangle, annulus, freehand).
    For freehand shapes, the drawn path is attached to the extraction parameters.

    Parameters
    ----------
    extraction_params : :class:`dict`
        The current extraction parameters stored in the `extraction-params` store.
        This includes the shape type, center coordinates, dimensions, angles, and
        the drawn path (if applicable).
    fig : :class:`dict`
        The current figure object for the `gonet-image` component, which is updated
        with the new shape.
    config : :class:`dict`
        The current configuration object for the `gonet-image` component, which is
        updated based on the selected shape.
    selected_shape : :class:`str`
        The currently selected shape type from the shape selector. Possible values
        are "circle", "rectangle", "annulus", and "freehand".
    path : :class:`str` or :data:`NoneType`
        The path of the freehand-drawn region, if applicable. If `None`, no freehand
        region is used.

    Returns
    -------
    tuple
        A tuple containing:
        - :class:`dict`: The updated figure object with the new shape.
        - :class:`dict`: The updated configuration object for the `gonet-image` component.

    Notes
    -----
    - For freehand shapes, the `path` is attached to the `extraction_params` and
      the figure's drag mode is set to "drawclosedpath".
    - For other shapes, the :class:`~GONet_Wizard.GONet_utils.src.extract_app.shapes.base.Shape` class is used to generate the shape and update
      the figure's layout.
      
    """

    extraction_params['shape'] = selected_shape

    if selected_shape == 'freehand':
        config["modeBarButtonsToAdd"] = ["drawclosedpath"]
        fig['layout']['dragmode'] = 'drawclosedpath'
        # Attaching path to ``extraction_params`` if we are in free hand
        # so that we can fetch tha previosly drawn path. However, it
        # won't be editable anymore.
        extraction_params['path'] = path
    else:
        config["modeBarButtonsToAdd"] = []
        fig['layout']['dragmode'] = 'zoom'

    try:
        shape = base.Shape.from_dict(extraction_params)
        fig["layout"]["shapes"] = shape.draw()

    except base.IncompleteShapeError:
        if "shapes" in fig["layout"]:
            del fig["layout"]['shapes']

    return fig, config


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

    path : :class:`list`
        The current freehand path data, typically a list with one shape dictionary
        containing the 'path' key.

    Returns
    -------
    :class:`list`
        The same `path` object, to be passed to the `save-path` store for download.
    """

    return path


@app.callback(
    Output("extraction-params", "data", allow_duplicate=True),
    Output("drawn-path", "data", allow_duplicate=True),
    #---------------------
    Input("upload-path", 'contents'),
    #---------------------
    State("extraction-params", "data"),
    #---------------------
    prevent_initial_call=True
)
def load_path(contents, extraction_params):
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
    extraction_params : :class:`dict`
        The current extraction parameters stored in the `extraction-params` store.
        This is updated to include the loaded path.

    Returns
    -------
    tuple
        A tuple containing:
        - :class:`dict`: Updated extraction parameters with the loaded path.
        - :class:`dict`: Parsed JSON content representing the freehand path data.

    """

    return extraction_params, load_json(contents)


@app.callback(
    Output("exit-button", "n_clicks"),
    #---------------------
    Input("extract-button", "n_clicks"),
    #---------------------
    State("extraction-params", "data"),
    State("exit-button", "n_clicks"),
    #---------------------
    prevent_initial_call=True
)
def extraction_button(_, extraction_params, n):
    """
    Store extraction parameters and programmatically trigger the exit button.

    This callback is triggered when the user clicks the "Extract" button.
    It stores the provided extraction parameters in the Flask server config
    so they can be accessed after the GUI closes, and then programmatically
    increments the click count of the "Exit" button to initiate application
    shutdown.

    Parameters
    ----------
    _ : :class:`int` or :data:`None`
        The number of times the "Extract" button has been clicked.
        This parameter is unused but required by Dash as the input trigger.
    extraction_params : :class:`dict`
        The extraction parameters retrieved from the ``extraction-params``
        `dcc.Store` component in the Dash layout.
    n : :class:`int` or :data:`None`
        The current number of clicks on the "Exit" button.

    Returns
    -------
    :class:`int`
        The updated click count for the "Exit" button, incremented by one
        from its current value (or set to 1 if it was previously ``None``),
        which triggers any callbacks listening to the exit event.
    """
    app.server.config["extraction_params"] = extraction_params
    return 1 if n is None else n+1


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
    import webview
    webview.windows[0].evaluate_js("window.pywebview.api.close_window()")
    return True