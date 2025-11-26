"""
GONet Dashboard Launcher
============================

Entry point for launching the GONet Dashboard.

This module imports the `Dash <https://dash.plotly.com/>`_ `app` instance and provides a top-level
function to start the server. The dashboard allows users to interactively explore GONet data,
view images, and analyze metadata. The dashboard can be launched from the command line
using the `dashboard` command. The command is declared via the :data:`COMMAND` constant, which
specifies the argument structure used by the centralized parser builder.

**Constants**

- :data:`COMMAND` : :class:`~GONet_Wizard.commands.cli_core.CommandSpec` object
  for the `dashboard` command.

**Functions**

- :func:`launch_GONet_dashboard` : Launch the GONet Dashboard server using `Dash <https://dash.plotly.com/>`_.

"""

from GONet_Wizard.GONet_dashboard.src.app import launch_dashboard
from GONet_Wizard.commands.cli_core import ExpandFilenames, CommandSpec, expand_inputs, filter_by_ext
from GONet_Wizard import settings
import argparse

COMMAND = CommandSpec(
    name="dashboard",
    help="Launch the interactive GONet dashboard.",
    args=[
        {
            "flags": ["--debug"],
            "action": "store_true",
            "default": settings.DASHBOARD_DEBUG.default,
            "help": "Run the dashboard in debug mode (more verbose logging)."
        },
        {
            "flags": ["--input"],
            "nargs": '+',
            "default": '.',
            "action": ExpandFilenames,
            "help": "Path to GONet data directory or JSON file(s). Default is current directory."
        },
        {
            "flags": ["--show_images_preview"],
            "action": "store_true",
            "default": False,
            "help": "Show image previews in the dashboard."
        },
        {
            "flags": ["--images_path"],
            "default": '.', 
            "help": "Path to GONet images directory. Default is current directory."
        },
    ],
)


def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler for the `dashboard` command.

    The `input` and `images_path` arguments are expanded using
    :func:`expand_inputs`, and filtered to include only JSON files.
    If no inputs are provided, the current directory is used by default.
    The dashboard is then launched with the specified parameters.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments.
    
    Returns
    -------
    None

    """

    if not hasattr(args, 'input') or not args.input:  # option omitted
        args.input = expand_inputs(['.'])
    else:
        args.input = expand_inputs(args.input)
    if args.show_images_preview and (not hasattr(args, 'images_path') or not args.images_path):  # option omitted
        args.images_path = expand_inputs(['.'])
    else:
        args.images_path = expand_inputs([args.images_path])

    args.input = filter_by_ext(args.input, ['.json', '.csv'])
    launch_dashboard(args.input, args.show_images_preview, args.images_path, args.debug)
