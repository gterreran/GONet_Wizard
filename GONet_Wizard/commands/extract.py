"""
GONet Pixel Extraction Command-Line Module
==========================================

This module provides command-line utility functions to extract pixel counts
from GONet image files. It supports different geometric selection shapes
(e.g., circles, rectangles, annuli, and free-form shapes) for region-of-interest
definition. The extraction can be triggered either through direct parameters
or by launching an interactive GUI.

The module validates user-provided parameters for the selected shape and ensures
that the extraction process is performed correctly. Results are saved to a JSON
file, with automatic handling of file overwrites.

Functions
---------
:func:`validate_output_file`
    Validate the output file path and ensure it does not overwrite an existing file.
:func:`comma_separated_pair`
    Parse and validate a string representing two comma-separated integers.
:func:`extract_counts_from_GONet`
    Perform counts extraction from one or more GONet files, using shape
    parameters provided by the user or launching the extraction GUI.

"""

import json
from typing import Union, List
from GONet_Wizard.GONet_utils.src.extractors import extract_all
from pathlib import Path

def validate_output_file(output: str) -> str:
    """
    Validate the output file path and ensure it does not overwrite an existing file.

    If the file already exists, an index is appended or incremented to create a unique filename.

    Parameters
    ----------
    output : :class:`str`
        Path to the output file.

    Returns
    -------
    str
        A unique output file path.

    Raises
    ------
    ValueError
        If the output file path is invalid.
    """
    if not output.endswith(".json"):
        raise ValueError("Output file must be a JSON file.")

    output_path = Path(output)
    if output_path.exists():
        print(f"Warning: {output} already exists.")
        # Generate a unique filename by appending or incrementing an index
        stem = output_path.stem
        suffix = output_path.suffix
        parent = output_path.parent

        index = 1
        while True:
            new_filename = parent / f"{stem}_{index}{suffix}"
            if not new_filename.exists():
                print(f"Saving to {new_filename} instead.")
                return str(new_filename)
            index += 1

    return output

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
    tuple of :class:`int`
        A tuple containing the two parsed integers.

    Raises
    ------
    ValueError
        If the input cannot be parsed into exactly two integers.
    """

    try:
        parts = [int(x) for x in value.split(',')]
        if len(parts) != 2:
            raise ValueError
        return parts[0], parts[1]
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
        inner_radius: float = None,
        outer_radius: float = None,
        angles: str = None,
        output: str = None
    ) -> None:
    """
    Extract pixel counts from one or more GONet image files.

    Depending on the provided `shape` parameter, the function validates
    associated geometric arguments (e.g. `center`, `radius`, `sides`, ...)
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
        - `"annulus"`: Requires `center`, `radius` or `inner_radius` and `outer_radius`.
        - `"free"` or None: Launch the interactive extraction GUI.

    center : :class:`str`, optional
        Center coordinates of the region, as `"x,y"` (pixels).

    radius : :class:`float`, optional
        Radius of the region (pixels) for `"circle"` or `"annulus"` shapes.

    sides : :class:`str`, optional
        Side lengths of the rectangle as `"width,height"` (pixels).

    inner_radius : :class:`float`, optional
        Inner radius (pixels) for the `"annulus"` shape. Either `inner_radius`
        or `radius` must be provided for annulus.
        
    outer_radius : :class:`float`, optional
        Outer radius (pixels) for the `"annulus"` shape.
    
    angles : :class:`str`, optional
        Start and end angles in degrees, as `"start_angle,end_angle"`.
        Defaults to `"-180,180"`.

    output : :class:`str`, optional
        Name of the output JSON file.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If required parameters for the chosen `shape` are missing or invalid.

    Notes
    -----
    - If none of `red`, `green`, or `blue` are True, all channels will be
      extracted by default.

    """

    # Check if files is a single string
    if isinstance(files, str):
        # Check if it's a comma-separated list
        if ',' in files:
            files = [f.strip() for f in files.split(',')]
        else:
            files = [files]

    # If all extensions are false, we will extract all of them
    if not any([red, green, blue]):
        extensions = ["red", "green", "blue"]
    else:
        extensions = []
        if red:
            extensions.append("red")
        if green:
            extensions.append("green")
        if blue:
            extensions.append("blue")

    extraction_params = {
        'shape': shape,
        'x0': None,
        'y0': None,
        'param1': None,
        'param2': None,
        'start_angle': -180,
        'end_angle': 180,
        'path': None
    }

    if angles is not None:
        extraction_params["start_angle"], extraction_params["end_angle"] = comma_separated_pair(angles, "angles")

    # Validate based on shape
    if shape in ["circle", "rectangle", "annulus"]:
        if center is None:
            raise ValueError(f"For shape {shape}, --center is required.")
        extraction_params['x0'], extraction_params['y0'] = comma_separated_pair(center, "center")

    if shape == "circle":
        if radius is None:
            raise ValueError(f"For shape {shape}, --radius is required.")
        extraction_params['param1'] = radius        

    elif shape == "annulus":
        if inner_radius is None or outer_radius is None:
            raise ValueError("For shape 'annulus', provide both --inner_radius and --outer_radius.")
        extraction_params['param1'] = inner_radius
        extraction_params['param2'] = outer_radius
        
    elif shape == "rectangle":
        if sides is None:
            raise ValueError(f"For shape {shape}, --sides is required.")
        extraction_params['param1'], extraction_params['param2'] = comma_separated_pair(sides, "sides")    

    # this include both shape=='free' and None
    else:
        # importing the gui only if I need it
        from GONet_Wizard.GONet_utils.src.extract_app.extract_gui import launch_extraction_gui
        extraction_params = launch_extraction_gui(files)
        if extraction_params:
            shape = extraction_params['shape']

    if extraction_params is None:
        print("Extraction parameters were not set. Exiting.")
        return

    print(f"Extracting {shape}")
    print(f"Channels - {', '.join(extensions)}")
    out_dict = extract_all(files, extensions, extraction_params)

    if output is None:
        output = f"extraction_{shape}.json"

    output = validate_output_file(output)
    

    with open(output, "w") as f:
        json.dump(out_dict, f, indent=4)
        print(f"Results saved to {output}")
