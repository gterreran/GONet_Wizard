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

The command is declared via the :data:`COMMAND` constant, which specifies the
argument structure used by the centralized parser builder. When invoked from the
CLI, the parser dispatches directly to :func:`cli_handler`, which translates the
parsed :class:`argparse.Namespace` into a call to the reusable plotting function.

Constants
---------
- :data:`COMMAND` : :class:`~GONet_Wizard.commands.cli_core.CommandSpec` object
  for the `extract` command.

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

import json, warnings, argparse
from typing import Union, List
from GONet_Wizard.GONet_utils.src.extractors import extract_all
from GONet_Wizard.GONet_utils import GONetFile
from pathlib import Path
from GONet_Wizard.commands.cli_core import ExpandFilenames, CommandSpec, filter_by_ext
from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)

_channel_flags = [
    {
        "flags": [f"--{c}"],
        "action": "store_true",
        "default": False,
        "help": f"Plot only the {c} channel."
    }
    for c in GONetFile.CHANNELS
]

COMMAND = CommandSpec(
    name="extract",
    help="Extract counts from a region one or more GONet files.",
    args=[
        {
            "flags": ["filenames"],
            "nargs": "*",
            "action": ExpandFilenames,
            "help": (
                "GONet file(s) to extract [.jpg, .tiff]. "
                "`*` wildcards and comma-separated lists are supported."
            ),
        },
        *_channel_flags,
        {
            "flags": ["--shape"],
            "choices": ["circle", "rectangle", "annulus", "interactive"],
            "help": (
                "Shape of the extraction region.  If shape is 'interactive', "
                "or no shape is parsed, the user will select the region interactively."
            ),
        },
        {
            "flags": ["--center"],
            "help": (
                "Center of the region in pixels, as 2 comma-separated values: x,y. "
                "Example: 1000,800"
            ),
        },
        {
            "flags": ["--radius"],
            "help": "Radius in pixels (required if shape is circle).",
        },
        {
            "flags": ["--sides"],
            "help": (
                "Sides in pixels, as 2 comma-separated values: x,y. width,height "
                "(required if shape is rectangle). Example: 300,400"
            ),
        },
        {
            "flags": ["--inner_radius"],
            "help": "Inner radius in pixels. (required if shape is annulus).",
        },
        {
            "flags": ["--outer_radius"],
            "help": "Outer radius in pixels (required if shape is annulus).",
        },
        {
            "flags": ["--angles"],
            "help": (
                "Angles in degrees, as 2 comma-separated values: start_angle,end_angle "
                "(optional). 0 degrees is along the +x axis, and angles increase counter-clockwise. "
            ),
        },
        {
            "flags": ["--output"],
            "help": (
                "Output file name. Default name is 'extraction_shape.json'. If files already exists, it will not be overwritten, but a new file will be created with sequential number added to it."
            ),
        },
        {
            "flags": ["--output_type"],
            "choices": ["json", "csv"],
            "help": "Output file type. Options are 'json' (default) or 'csv'.",
        },
        {
            "flags": ["--debug"],
            "action": "store_true",
            "default": False,
            "help": "Run the extraction GUI in debug mode.",
        },
        {
            "flags": ["--port"],
            "type": int,
            "default": 8051,
            "help": "Port for the extraction GUI Dash server.",
        },
    ],
)


def validate_output_file(output: str, output_type: str) -> Union[str, str]:
    """
    Validate the output file path and ensure it does not overwrite an existing file.

    If the file already exists, an index is appended or incremented to create a unique filename.

    Parameters
    ----------
    output : :class:`str`
        Path to the output file.
    output_type : :class:`str`
        Type of the output file, either "json" or "csv".

    Returns
    -------
    tuple of :class:`str`
        A unique output file path and the output type.

    Raises
    ------
    ValueError
        If the output file path is invalid.
    """
    
    # Check output is a valid filename with correct extension
    if '.' not in output:
        if output_type is None:
            warnings.warn(
                "The wanted extension for the output file is not specified. Defaulting to 'json'.",
                RuntimeWarning,
            )
            output = f'{output}.json'
        else:
            output = f'{output}.{output_type}'
    else:
        ext = output.split('.')[-1].lower()
        if ext not in ['json', 'csv']:
            raise ValueError(f"Output file must have .json or .csv extension. Provided: {ext}")
        if output_type is not None and ext != output_type:
            warnings.warn(
                f"Output file extension '{ext}' does not match specified output_type '{output_type}'. Ignoring output_type and using the extension in the provided output file ({ext}).",
                RuntimeWarning,
            )

        output_type = ext

    output_path = Path(output)
    if output_path.exists():
        logger.warning("%s already exists.", output)
        # Generate a unique filename by appending or incrementing an index
        stem = output_path.stem
        suffix = output_path.suffix
        parent = output_path.parent

        index = 1
        while True:
            new_filename = parent / f"{stem}_{index}{suffix}"
            if not new_filename.exists():
                logger.info("Saving to %s instead.", new_filename)
                return str(new_filename), output_type
            index += 1

    # Check if the parent directory exists, and create it if it doesn't
    if not output_path.parent.exists():
        logger.info("Directory %s does not exist. Creating it.", output_path.parent)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    return output, output_type

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
        output: str = None,
        output_type: str = None,
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

    output_type : :class:`str`, optional
        Type of the output file, either "json" or "csv". Defaults to "json

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

    # Validate output
    if output is None:
        if output_type is None:
            output_type = "json"
        output = f"extraction_{shape}.{output_type}"

    output, output_type = validate_output_file(output, output_type)

    # Check if files is a single string
    if isinstance(files, str):
        # Check if it's a comma-separated list
        if ',' in files:
            files = [f.strip() for f in files.split(',')]
        else:
            files = [files]

    # If all channels are false, we will extract all of them
    if not any([red, green, blue]):
        channels = ["red", "green", "blue"]
    else:
        channels = []
        if red:
            channels.append("red")
        if green:
            channels.append("green")
        if blue:
            channels.append("blue")

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
        logger.info("Extraction parameters were not set. Exiting.")
        return

    logger.info("Extracting %s", shape)
    logger.info("Channels: %s", ", ".join(channels))
    out_epoch_list = extract_all(files, channels, extraction_params)
    
    for epoch in out_epoch_list:
        epoch["files"] = str(epoch["files"])  # ensure filepaths are strings for JSON serialization

    if output_type == "csv":
        import pandas as pd
        df = pd.json_normalize(out_epoch_list, sep="_")
        df.to_csv(output, index=False)
        logger.info("Results saved to %s", output)

    else:
        with open(output, "w") as f:
            json.dump(out_epoch_list, f, indent=4)
            logger.info("Results saved to %s", output)


def cli_handler(args: argparse.Namespace):
    files = args.filenames or [Path(".")]
    files = filter_by_ext(files, [".jpg", ".jpeg", ".tiff", ".tif"])

    if args.shape in {None, "interactive"}:
        from GONet_Wizard.GONet_utils.src.extract_app.extract_gui import (
            ensure_extraction_gui_running,
        )
        from GONet_Wizard.commands.ui_bridge import WindowRequest
        from GONet_Wizard.ui.windows import WindowSpec

        url = ensure_extraction_gui_running(
            data_files=[str(p) for p in files],
            debug=bool(args.debug),
            port=int(args.port),
        )

        return WindowRequest(
            key="extract-gui",
            spec=WindowSpec(
                title="GONet Wizard Extraction GUI",
                url=url,
                width=1250,
                height=750,
            ),
        )

    extract_counts_from_GONet(
        files=files,
        red=args.red,
        green=args.green,
        blue=args.blue,
        shape=args.shape,
        center=args.center,
        radius=float(args.radius) if args.radius is not None else None,
        sides=args.sides,
        inner_radius=float(args.inner_radius) if args.inner_radius is not None else None,
        outer_radius=float(args.outer_radius) if args.outer_radius is not None else None,
        angles=args.angles,
        output=args.output,
        output_type=args.output_type,
    )