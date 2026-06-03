
"""
Build the Full-Array command
==============================

This module defines the `build_full_array` command for the GONet Wizard CLI.
The :data:`COMMAND` constant is defined here, which parses the command-line
arguments for building a full-array GONet image.

**Constants**

- :data:`COMMAND` : :class:`~GONet_Wizard.commands.cli_core.CommandSpec` object
  for the `build_full_array` command.

**Functions**

- :func:`cli_handler` : CLI handler for the `build_full_array` command.

"""
import argparse, warnings
from GONet_Wizard.commands.cli_core import ExpandFilenames, CommandSpec, filter_by_ext
from GONet_Wizard.GONet_utils.src.gonet.analysis_utils.full_array import build_full_array
from pathlib import Path

COMMAND = CommandSpec(
    name="build_full_array",
    help="Build full-array GONet image by histogram matching and "
            "combining Bayer channels.",
    args=[
        {
            "flags": ["input"],
            "nargs": "+",
            "action": ExpandFilenames,
            "help": (
                "Input GONet RAW (*.jpg) file, or list of files. "
                "If a folder is provided, all *.jpg files in the folder will be used."
            ),
        },
        {
            "flags": ["--show"],
            "action": "store_true",
            "help": "Show diagnostic plots (histograms, KDEs, combined image).",
        },
        {
            "flags": ["--outfile"],
            "type": str,
            "default": None,
            "help": (
                "Output file name (default: <input_basename>_full_array.npz)."
            ),
        },
        {
            "flags": ["--verbose"],
            "action": "store_true",
            "help": "Enable verbose logging (INFO level).",
        },
        {
            "flags": ["--weights"],
            "type": str,
            "default": None,
            "help": (
                "Optional channel weights as comma-separated name=value pairs, "
                "e.g. 'red=0.25,green1=0.5,green2=0.5,blue=0.25'. "
                "Missing channels default to 1.0; extra names are ignored."
            ),
        },
    ]
)

def parse_channel_weights(weights: str | None) -> dict[str, float] | None:
    if weights is None:
        return None

    parsed = {}

    for item in weights.split(","):
        item = item.strip()
        if not item:
            continue

        if "=" not in item:
            raise ValueError(
                f"Invalid weight entry '{item}'. Expected format name=value."
            )

        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()

        if not name:
            raise ValueError("Channel weight name cannot be empty.")

        try:
            parsed[name] = float(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid weight value '{value}' for channel '{name}'."
            ) from exc

    return parsed

def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler for the `build_full_array` command.

    The `input` argument is expanded using :func:`~GONet_Wizard.commands.cli_core.expand_inputs`, and filtered
    to include only RAW ``.jpg`` files. For each input file, the full-array image
    is built using :func:`~GONet_Wizard.GONet_utils.src.gonet.analysis_utils.full_array.build_full_array` with the specified parameters.

    If multiple input files are provided and an `outfile` is specified, the
    `outfile` is treated as a suffix to be appended to each output file name.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments.
    
    Returns
    -------
    None
    
    """
    files = filter_by_ext(args.input, [".jpg"])
    # If more than one file, outfile will be used as a suffix basename

    out = args.outfile
    if out is None:
        outfiles = [None] * len(files)
    else:
        if isinstance(out, str):
            out = Path(out)
        if out.suffix != '':
            if out.suffix != '.npz':
                warnings.warn(
                    f"Output extension '{out.suffix}' will be ignored. Using '.npz' instead.",
                    UserWarning
                )
            out = out.stem
        if len(files) == 1:
            outfiles = [f"{out}.npz"]
        else:
            warnings.warn(
                f"Multiple input files detected; appending \"_{out}.npz\" as a suffix to each output file.",
                UserWarning
            )
            outfiles = []
            for f in files:
                outfiles.append(Path(f"{f.stem}_{out}.npz"))

    channel_weights = parse_channel_weights(args.weights)

    for i, f in enumerate(files):
        build_full_array(
            gonet_file=f,
            show=args.show,
            outfile=outfiles[i],
            verbose=args.verbose,
            channel_weights=channel_weights,
        )