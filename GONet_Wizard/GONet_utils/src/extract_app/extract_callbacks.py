"""
Defines the core interactivity for the GONet extraction GUI via Dash callbacks.

This module wires together user interactions with the UI elements defined in
`extract_layout.py`. It updates the displayed image, overlays shape-based masks,
computes extraction statistics, handles freehand drawing and path saving/loading,
and manages the state of shape-specific components. It also registers a
client-side callback for JSON downloads of the drawn region.

**Functions**

- :func:`update_figure_and_shape_options`:
    Main callback for updating the image, drawing shapes, computing statistics,
    and controlling visibility of shape-specific inputs and buttons based on
    user selections and inputs.

- :func:`save_path`:
    Callback for saving the drawn freehand path to internal state (`save-path`),
    triggered by the "Save" button.

- :func:`load_path`:
    Callback for loading a saved freehand path from uploaded content,
    triggered by the "Load" button.

**Notes**

- Shapes supported: circle, rectangle, annulus, freehand.
- Statistics returned: total counts, mean, std dev, and number of selected pixels.
- Path data is stored and shared using `dcc.Store` components with ids
  ``freehand-path``, ``save-path``, and ``load-path``.

"""

from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from dash import Input, Output, State, ctx, no_update
from GONet_Wizard.GONet_utils.src.extract import mask_sector, mask_annular_sector, mask_from_closed_path, extract_region
from GONet_Wizard.GONet_dashboard.src.load_save_callbacks import register_json_download, load_json
from GONet_Wizard.GONet_utils.src.extract_app.extract_server import app
from GONet_Wizard.GONet_utils.src.extract_app.shapes import sector_path, annulus_sector_path, rectangle_sector_path


@app.callback(
    Output("gonet_image", "figure"),
    Output("circle-options", "style"),
    Output("rectangle-options", "style"),
    Output("annulus-options", "style"),
    Output("freehand-options", "style"),
    Output("freehand-reset-button", "disabled"),
    Output("freehand-save-button", "disabled"),
    Output("freehand-path", "data"),
    Output("stat-total", "children"),
    Output("stat-mean", "children"),
    Output("stat-std", "children"),
    Output("stat-npix", "children"),
    #---------------------
    Input("file-selector", "value"),
    Input("channel-selector", "value"),
    Input("shape-selector", "value"),

    # Circle
    Input("circle-center-x", "value"),
    Input("circle-center-y", "value"),
    Input("circle-radius", "value"),
    Input("circle-sector-start", "value"),
    Input("circle-sector-end", "value"),

    # Rectangle
    Input("rectangle-center-x", "value"),
    Input("rectangle-center-y", "value"),
    Input("rectangle-side1", "value"),
    Input("rectangle-side2", "value"),
    Input("rectangle-sector-start", "value"),
    Input("rectangle-sector-end", "value"),

    # Annulus
    Input("annulus-center-x", "value"),
    Input("annulus-center-y", "value"),
    Input("annulus-outer-radius", "value"),
    Input("annulus-inner-width", "value"),
    Input("annulus-sector-start", "value"),
    Input("annulus-sector-end", "value"),

    #Free hand
    Input("gonet_image", "relayoutData"),
    Input("load-path", "data"),
    Input("freehand-reset-button", "n_clicks"),
    #---------------------
    State("gonet_image", "figure"),
    State("freehand-path", "data"),
)
def update_figure_and_shape_options(selected_file, selected_channel, selected_shape, cx, cy, r, ca1, ca2, rx, ry, s1, s2, ra1, ra2, ax, ay, aor, air, aa1, aa2, fh, fh_load, reset, fig, path_data):
    """
    Callback to update the main image figure, region overlay, shape controls,
    and computed extraction statistics based on user interaction.

    This function handles:

    - Loading the image when a file or channel is selected.
    - Switching between shape modes and revealing the appropriate input widgets.
    - Drawing shapes on the figure based on input values.
    - Computing extraction statistics from the selected region.
    - Managing freehand drawing and path interaction (reset/load/save).

    Parameters
    ----------
    selected_file : :class:`str`
        Path to the selected GONet file.

    selected_channel : :class:`str`
        Selected color channel to display ("red", "green", or "blue").

    selected_shape : :class:`str`
        One of "circle", "rectangle", "annulus", or "freehand".

    cx : :class:`float`
        X-coordinate of the circle center.

    cy : :class:`float`
        Y-coordinate of the circle center.

    r : :class:`float`
        Radius of the circle.

    ca1 : :class:`float`
        Start angle of the circle sector, in degrees.

    ca2 : :class:`float`
        End angle of the circle sector, in degrees.

    rx : :class:`float`
        X-coordinate of the rectangle center.

    ry : :class:`float`
        Y-coordinate of the rectangle center.

    s1 : :class:`float`
        First side length of the rectangle.

    s2 : :class:`float`
        Second side length of the rectangle.

    ra1 : :class:`float`
        Start angle of the rectangle sector, in degrees.

    ra2 : :class:`float`
        End angle of the rectangle sector, in degrees.

    ax : :class:`float`
        X-coordinate of the annulus center.

    ay : :class:`float`
        Y-coordinate of the annulus center.

    aor : :class:`float`
        Outer radius of the annulus.

    air : :class:`float`
        Inner width of the annulus (distance between outer and inner radius).

    aa1 : :class:`float`
        Start angle of the annulus sector, in degrees.

    aa2 : :class:`float`
        End angle of the annulus sector, in degrees.

    fh : :class:`dict`
        `relayoutData` from the figure containing new freehand shape info.

    fh_load : :class:`dict`
        JSON data from a previously saved freehand path.

    reset : :class:`int` or :class:`NoneType`
        Click count of the reset button.

    fig : :class:`dict`
        The current Plotly figure dictionary to update.

    path_data : :class:`list`
        List of shape dictionaries representing the drawn freehand path.

    Returns
    -------
    fig : :class:`dict`
        Updated Plotly figure including image and drawn shapes.

    output_circle_options : :class:`dict`
        Visibility style for the circle shape controls.

    output_rectangle_options : :class:`dict`
        Visibility style for the rectangle shape controls.

    output_annulus_options : :class:`dict`
        Visibility style for the annulus shape controls.

    output_freehand_options : :class:`dict`
        Visibility style for the freehand shape controls.

    output_freehand_reset_button : :class:`bool`
        Whether the freehand reset button should be disabled.

    output_freehand_save_button : :class:`bool`
        Whether the freehand save button should be disabled.

    path_data : :class:`list`
        Updated freehand path data.

    output_stat_total : :class:`float` or :class:`str`
        Total counts within the selected region, or empty string if invalid.

    output_stat_mean : :class:`float` or :class:`str`
        Mean pixel value in the region, or empty string if invalid.

    output_stat_std : :class:`float` or :class:`str`
        Standard deviation of pixel values, or empty string if invalid.

    output_stat_npix : :class:`int` or :class:`str`
        Number of pixels within the region, or empty string if invalid.
    """

    # Initialize all outputs
    # fig is always changed in a way or another, so fig will always returned.
    output_circle_options = no_update
    output_rectangle_options = no_update
    output_annulus_options = no_update
    output_freehand_options = no_update
    output_freehand_reset_button = no_update
    output_freehand_save_button = no_update
    output_stat_total = no_update
    output_stat_mean = no_update
    output_stat_std = no_update
    output_stat_npix = no_update

    def visible(s):
        return {"display": "block"} if selected_shape == s else {"display": "none"}

    if len(fig['data'][0]['z']) == 0 or ctx.triggered_id in ['file-selector', 'channel-selector', None]:
        gof = GONetFile.from_file(selected_file)
        fig['data'][0]['z'] = gof.channel(selected_channel)
        del gof

    if ctx.triggered_id == 'shape-selector':
        
        fig["layout"]["shapes"] = []

        fig['layout']['dragmode'] = 'zoom'

        if selected_shape == "freehand":
            fig['layout']['dragmode'] = 'drawclosedpath'

        output_circle_options = visible("circle")
        output_rectangle_options = visible("rectangle")
        output_annulus_options = visible("annulus")
        output_freehand_options = visible("freehand")

                        
    # if "shapes" not in fig["layout"] or ctx.triggered_id == 'shape-selector':
    #     fig["layout"]["shapes"] = []

    if selected_shape == "circle":
        if None in (cx, cy, r, ca1, ca2):
            output_stat_total = ''
            output_stat_mean = ''
            output_stat_std = ''
            output_stat_npix = ''
        else:
            fig["layout"]["shapes"] = sector_path(cx, cy, r, ca1, ca2)

            mask = mask_sector(fig['data'][0]['z'], cx, cy, r, ca1, ca2)
            output = extract_region(fig['data'][0]['z'], mask)
            output_stat_total = output.total_counts
            output_stat_mean = output.mean_counts
            output_stat_std = output.std
            output_stat_npix = output.npixels

    elif selected_shape == "rectangle":
        if None in (rx, ry, s1, s2, ra1, ra2):
            output_stat_total = ''
            output_stat_mean = ''
            output_stat_std = ''
            output_stat_npix = ''
        else:
            fig["layout"]["shapes"] = rectangle_sector_path(rx, ry, s1, s2, ra1, ra2)

            mask = mask_from_closed_path(fig['data'][0]['z'], fig["layout"]["shapes"])
            output = extract_region(fig['data'][0]['z'], mask)
            output_stat_total = output.total_counts
            output_stat_mean = output.mean_counts
            output_stat_std = output.std
            output_stat_npix = output.npixels

    elif selected_shape == "annulus":
        if None in (ax, ay, aor, air, aa1, aa2):
            output_stat_total = ''
            output_stat_mean = ''
            output_stat_std = ''
            output_stat_npix = ''
        else:
            fig["layout"]["shapes"] = annulus_sector_path(ax, ay, aor, air, aa1, aa2)

            mask = mask_annular_sector(fig['data'][0]['z'], ax, ay, aor, air, aa1, aa2)
            output = extract_region(fig['data'][0]['z'], mask)
            output_stat_total = output.total_counts
            output_stat_mean = output.mean_counts
            output_stat_std = output.std
            output_stat_npix = output.npixels

    elif selected_shape == "freehand":
        if ctx.triggered_id == 'gonet_image':
            if 'shapes' in fh:
                # keep only the last shape drawn
                path_data = [fig["layout"]["shapes"][-1]]
            else:
                path_data[0]['path']=fh['shapes[0].path']
            output_freehand_reset_button = False
            output_freehand_save_button = False
        elif ctx.triggered_id == 'load-path':
            path_data = fh_load
            output_freehand_reset_button = False
            output_freehand_save_button = False
        elif ctx.triggered_id == 'freehand-reset-button':
            fig["layout"]["shapes"] = []
            path_data = []
            output_freehand_reset_button = True
            output_freehand_save_button = True
        if len(path_data)>0:
            fig["layout"]["shapes"] = path_data[:]
            mask = mask_from_closed_path(fig['data'][0]['z'], path_data[0]['path'])
            output = extract_region(fig['data'][0]['z'], mask)
            output_stat_total = output.total_counts
            output_stat_mean = output.mean_counts
            output_stat_std = output.std
            output_stat_npix = output.npixels
        else:
            output_stat_total = ''
            output_stat_mean = ''
            output_stat_std = ''
            output_stat_npix = ''
        


    return fig, output_circle_options, output_rectangle_options, output_annulus_options, output_freehand_options, output_freehand_reset_button, output_freehand_save_button, path_data, output_stat_total, output_stat_mean, output_stat_std, output_stat_npix


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
    State("freehand-path", "data"),
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
    Output("load-path", "data"),
    #---------------------
    Input("upload-path", 'contents'),
    #---------------------
    prevent_initial_call=True
)
def load_path(contents):
    """
    Callback to load a previously saved freehand path from uploaded JSON content.

    This function is triggered when the user uploads a JSON file via the upload
    component. The JSON is parsed and returned for use as the current path.

    Parameters
    ----------
    contents : :class:`str`
        Base64-encoded contents of the uploaded JSON file, as returned by
        Dash's `dcc.Upload` component.

    Returns
    -------
    :class:`dict`
        Parsed JSON content representing the freehand path data.
    """
    return load_json(contents)


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