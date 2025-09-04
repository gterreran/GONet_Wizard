"""
Defines the core interactivity for the GONet extraction GUI via Dash callbacks.

This module wires together user interactions with the UI elements defined in
`extract_layout.py`. It updates the displayed image, overlays shape-based masks,
computes extraction statistics, handles freehand drawing and path saving/loading,
and manages the state of shape-specific components. It also registers a
client-side callback for JSON downloads of the drawn region.

**Functions**

- :func:`load_gonet_file`:
    Loads the GONet file for the selected file.

- :func:`store_binning`:
    Stores the binning information for the current extraction.

- :func:`update_figure_heatmap`:
    Update the heatmap figure based on the selected channel and binning option.

- :func:`update_shape_options`:
    Updates visibility and labels of shape-specific input fields based on selected shape.
    Also updates the figure drawing settings based on the shape selected.

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

- :func:`extraction_button`:
    Stores extraction parameters and programmatically triggers the "Exit" button.

- :func:`exit_app`:
    Requests closing the PyWebView window when the "Exit" button is clicked.

**Notes**

- Shapes supported: circle, rectangle, annulus, freehand.
- Statistics returned: total counts, mean, std dev, and number of selected pixels.

"""

import os, copy
from dash import Input, Output, State, ctx, no_update
from dash_extensions.enrich import Serverside
from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from GONet_Wizard.GONet_utils.src.extractors import extract_counts_from_region, extraction_output
from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import register_json_download, load_json
from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
import GONet_Wizard.GONet_utils.src.extract_app.shapes.base as base
from GONet_Wizard.GONet_utils.src.extract_app.extract_layout import files_path
import numpy as np

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
    This is the only callback in the module without `prevent_initial_call=True`,
    meaning it runs automatically when the app loads. This ensures that the
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
    Output("gonet-image", "figure", allow_duplicate=True),
    Output("gonet-image", "config"),
    Output("shape-options", "style"),
    Output("freehand-options", "style"),
    Output("shape-extra-parameters", "children"),
    Output("shape-parameter1", "placeholder"),
    Output("shape-parameter2", "style"),
    Output("shape-parameter2", "placeholder"),
    Output("config-done-dummy-div", "children"),
    #---------------------
    Input("heatmap-ready-control", "children"),
    Input("shape-selector", "value"),
    #---------------------
    State("gonet-image", "figure"),
    State("gonet-image", "config"),
    prevent_initial_call=True
)
def update_shape_options(_, selected_shape, fig, config):
    """
    Update visibility and labels of shape-specific input fields based on selected shape.
    Also update the figure drawing settings based on the shape selected.

    This callback adjusts the visibility of input fields and buttons related to
    shape parameters depending on the user's selection in the shape dropdown.
    It ensures that only relevant inputs are shown for the chosen shape type.

    This callback also updates the `gonet-image` component's configuration and dragmode
    based on whether the selected shape is freehand or not.

    To guarantee the correct sequence of callbacks, this callback waits on the
    :func:`.update_figure_heatmap` callback to complete before executing, by listening to
    changes to the `heatmap-ready-control` component.

    Parameters
    ----------
    _ : :class:`str` or :class:`NoneType`
        Dummy Div triggered by :func:`.update_figure` when the figure is ready (ignored).

    selected_shape : :class:`str`
        The currently selected shape type from the dropdown. Possible values are
        "circle", "rectangle", "annulus", and "freehand".

    Returns
    -------
    tuple
        A tuple containing:

        - :class:`dict` or :data:`dash.no_update`: Updated figure object.
        - :class:`dict` or :data:`dash.no_update`: Updated figure configuration object.
        - :class:`dict`: CSS style for the shape options container (to show/hide it).
        - :class:`dict`: CSS style for the freehand options container (to show/hide it).
        - :class:`str` or :data:`dash.no_update`: Label text for extra parameters.
        - :class:`str` or :data:`dash.no_update`: Placeholder text for parameter 1 input.
        - :class:`dict` or :data:`dash.no_update`: CSS style for parameter 2 input (to show/hide it).
        - :class:`str` or :data:`dash.no_update`: Placeholder text for parameter 2 input.
        - :class:`str`: An empty string to update the `config-done-dummy-div` component,
          which serves as control for the extraction-params component.

    """

    # Making a copy of the item we started with
    figure_in = fig['layout']['dragmode']

    if selected_shape == 'freehand':
        config["modeBarButtonsToAdd"] = ["drawclosedpath"]
        fig['layout']['dragmode'] = 'drawclosedpath'
    else:
        config["modeBarButtonsToAdd"] = []
        fig['layout']['dragmode'] = 'zoom'

    # Checking if the dragmode changed. If not,
    # neither has the config
    if figure_in == fig['layout']['dragmode']:
        fig = no_update
        config = no_update

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

    return fig, config, output_shape_options, output_freehand_options, output_shape_extra_parameters, output_shape_parameter1_placeholder, output_shape_parameter2_style, output_shape_parameter2_placeholder, ''


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
        fig['data'][1]['z'] = []
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
    Output("mask", "data"),
    Output("extracted-values", "data"),
    Output("error-banner", "children"),
    Output("error-banner", "style"),
    #---------------------
    Input("config-done-dummy-div", "children"),
    Input("shape-center-x", "value"),
    Input("shape-center-y", "value"),
    Input("shape-parameter1", "value"),
    Input("shape-parameter2", "value"),
    Input("shape-sector-start", "value"),
    Input("shape-sector-end", "value"),
    #---------------------
    State("shape-selector", "value"),
    State("drawn-path", "data"),
    State("gonet_file", "data"),
    State("channel-selector", "value"),
    State("mask", "data"),
    State("error-banner", "style"),
    prevent_initial_call=True
)
def update_extraction_params(_, center_x, center_y, param1, param2, start_angle, end_angle, selected_shape, path, gof, channel, masked_figure, error_banner_style):
    """
    Update extraction parameters based on user inputs.

    This callback updates the `extraction-params` store with the current values
    of the shape parameters entered by the user. The updated extraction parameters
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
    error_banner_style : :class:`dict`
        The current style properties for the error banner.

    Returns
    -------
    tuple
        A tuple containing:
        
        - :class:`dict` with updated extraction parameters.
        - :class:`list` with the updated masked figure data.
        - :class:`Serverside` the :class:`~GONet_Wizard.GONet_utils.src.extract_app.extractors.extraction_output`
          object with the extracted values.
        - :class:`str` with any error messages for the banner.
        - :class:`dict` with the updated visibility style properties for the error banner.

    """

    error_banner_children = ''
    error_banner_style["visibility"] = 'hidden'

    extraction_params = {
        'shape': selected_shape,
        'x0': center_x,
        'y0': center_y,
        'param1': param1,
        'param2': param2,
        'start_angle': start_angle,
        'end_angle': end_angle,
        'path': path
    }

    masked_figure_initial = masked_figure[:]

    data = gof.get_channel(channel)

    try:
        shape = base.Shape.from_dict(extraction_params)
    except base.IncompleteShapeError:
        output = extraction_output(0, 0, 0, 0)
        masked_figure = []
    except (ValueError, TypeError) as e:
        error_banner_style["visibility"] = ["visible"]
        return no_update, no_update, no_update, str(e), error_banner_style
    else:
        mask = shape.mask(data)
        masked_figure = np.where(mask, 1, np.nan)
        masked_figure = masked_figure.tolist()
        output = extract_counts_from_region(data, mask)
        

    if masked_figure_initial != masked_figure:
        return extraction_params, masked_figure, Serverside(output, key="extraction_output"), error_banner_children, error_banner_style
    else:
        return no_update, no_update, no_update, error_banner_children, error_banner_style


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
    masked_figure : :class:`list`
        The current masked figure data stored in the `mask` store.
    extracted_values : :class:`~GONet_Wizard.GONet_utils.src.extract_app.extractors.extraction_output`
          object with the extracted values.
    

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

    try:
        shape = base.Shape.from_dict(extraction_params)
    except base.IncompleteShapeError:
        del fig["layout"]["shapes"]
        fig["data"][1]['z'] = []
    else:
        fig["layout"]["shapes"] = shape.draw()
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
    State("drawn-path", "data"),
    State("exit-button", "n_clicks"),
    #---------------------
    prevent_initial_call=True
)
def extraction_button(_, extraction_params, path, n):
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
    path : :class:`str` or :data:`NoneType`
        The path of the freehand-drawn region, if applicable. If `None`, no freehand
        region is used.
    n : :class:`int` or :data:`None`
        The current number of clicks on the "Exit" button.

    Returns
    -------
    :class:`int`
        The updated click count for the "Exit" button, incremented by one
        from its current value (or set to 1 if it was previously ``None``),
        which triggers any callbacks listening to the exit event.
    """

    extraction_params['path'] = path

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