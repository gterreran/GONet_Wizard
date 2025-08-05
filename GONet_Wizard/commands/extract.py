"""
This module provides command-line utility functions to extract pixel counts
from GONet image files. It supports different geometric selection shapes
(e.g., circles, rectangles, annuli, and free-form shapes) for region-of-interest
definition. The extraction can be triggered either through direct parameters
or by launching an interactive GUI.

Functions
---------
- :func:`comma_separated_pair`:
    Parse and validate a string representing two comma-separated integers.
- :func:`extract_counts_from_GONet`:
    Perform counts extraction from one or more GONet files, using shape
    parameters provided by the user or launching the extraction GUI.

Notes
-----
- The `extract_counts_from_GONet` function validates input parameters
  according to the selected shape.
- If no color channels are specified (`red`, `green`, `blue`), all channels
  are extracted by default.
- For shapes not specified or set to `'free'`, an interactive extraction
  GUI will be launched.


"""

import argparse
from typing import Union, List
from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from GONet_Wizard.GONet_utils.src.extract_app.extract_gui import launch_extraction_gui

def comma_separated_pair(value, name):
    """
    Parse and validate a string containing two comma-separated integers.

    This function splits the provided string by commas, converts both
    parts to integers, and verifies that exactly two integers are present.

    Parameters
    ----------
    value : :class:`str`
        String containing two integers separated by a comma (e.g., `"100,200"`).

    name : :class:`str`
        The name of the parameter (used in error messages).

    Returns
    -------
    :class:`list` of :class:`int`
        A list containing exactly two integers parsed from the input string.

    Raises
    ------
    ValueError
        If the input cannot be parsed into exactly two integers.
    """

    try:
        parts = [int(x) for x in value.split(',')]
        if len(parts) != 2:
            raise ValueError
        return parts
    except ValueError:
        raise ValueError(f"--{name} must be two comma-separated integers.")

def extract_counts_from_GONet(
        files: Union[str, List[str]],
        red: bool = False,
        green: bool = False,
        blue: bool = False,
        shape: str = None,
        center : str = None,
        radius: float = None,
        sides: str = None,
        width: float = None
    ) -> None:
    """
    Extract pixel counts from one or more GONet image files.

    Depending on the provided `shape` parameter, the function validates
    associated geometric arguments (`center`, `radius`, `sides`, `width`)
    and performs counts extraction from the specified regions. If no shape
    is given or `shape` is set to `'free'`, the interactive extraction GUI
    is launched.

    Parameters
    ----------
    files : :class:`str` or :class:`list` of :class:`str`
        Path(s) to one or more GONet image files to process.

    red : :class:`bool`, optional
        If True, extract counts from the red channel. Defaults to False.

    green : :class:`bool`, optional
        If True, extract counts from the green channel. Defaults to False.

    blue : :class:`bool`, optional
        If True, extract counts from the blue channel. Defaults to False.

    shape : :class:`str`, optional
        Shape of the extraction region. Supported values:
        
        - `"circle"`: Requires `center` and `radius`.
        - `"rectangle"`: Requires `center` and `sides`.
        - `"annulus"`: Requires `center`, `radius`, and `width`.
        - `"free"` or None: Launch the interactive extraction GUI.

    center : :class:`str`, optional
        Center coordinates of the region, as `"x,y"` (pixels).

    radius : :class:`float`, optional
        Radius of the region (pixels) for `"circle"` or `"annulus"` shapes.

    sides : :class:`str`, optional
        Side lengths of the rectangle as `"width,height"` (pixels).

    width : :class:`float`, optional
        Width of the annulus region (pixels), required for `"annulus"`.

    Raises
    ------
    ValueError
        If required parameters for the chosen `shape` are missing or invalid.

    Notes
    -----
    - If none of `red`, `green`, or `blue` are True, all channels will be
      extracted by default.

    """

    # If all extensions are false, we will extract all them
    if not any(extensions := [red, green, blue]):
        extensions =  [not el for el in extensions]

    # Validate based on shape
    if shape == "circle":
        if center is None or radius is None:
            raise ValueError("For shape 'circle', both --center and --radius are required.")
        center = comma_separated_pair(center, "center")
        try:
            radius = float(radius)
        except ValueError:
            argparse.ArgumentTypeError("--radius must be a float.")

    elif shape == "rectangle":
        if center is None or sides is None:
            raise ValueError("For shape 'rectangle', both --center and --sides are required.")
        center = comma_separated_pair(center, "center")
        sides = comma_separated_pair(sides, "sides")

    elif shape == "annulus":
        if center is None or radius is None or width is None:
            raise ValueError("For shape 'annulus', all --center, --radius and --width are required.")
        center = comma_separated_pair(center, "center")
        try:
            radius = float(radius)
        except ValueError:
            raise ValueError("--radius must be a float.")
        try:
            width = float(width)
        except ValueError:
            raise ValueError("--width must be a float.")
    # this include both shape=='free' and None
    else:
        launch_extraction_gui(files)
        

    for gof in files:
        go = GONetFile.from_file(gof)
