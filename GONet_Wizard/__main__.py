"""
GONet Wizard Command-Line Interface.

The GONet Wizard package provides a command-line interface for interacting
with GONet devices, launching the dashboard, and inspecting or plotting GONet data.
It allows users to:

- Visualize GONet images (`show`)
- View metadata from GONet files (`show_meta`)
- Launch the interactive dashboard (`dashboard`)
- Connect to a remote camera and run imaging-related commands (`connect`)

This CLI is launched using the :mod:`GONet_Wizard.__main__` module.

**Classes**

- ExpandFilenames: Custom argparse action to expand wildcard and comma-separated filenames.

"""



import argparse, glob
from GONet_Wizard import commands
from GONet_Wizard._version import __version__

class ExpandFilenames(argparse.Action):
    """
    Custom argparse action to expand wildcard and comma-separated filenames.

    This class allows command-line arguments that specify multiple files
    using wildcards (e.g., `*.tiff`) or comma-separated lists (e.g., `file1,file2`)
    to be automatically expanded into full lists of matching filenames.

    """

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Expand input values into individual filenames and assign to namespace.

        Parameters
        ----------
        parser : :class:`argparse.ArgumentParser`
            The parser instance calling this action.

        namespace : :class:`argparse.Namespace`
            The namespace object that holds parsed arguments.

        values : :class:`list` of :class:`str`
            The list of raw input values provided by the user.

        option_string : :class:`str`, optional
            The option string that was used to invoke this action (e.g., '--files').

        """
        expanded = []
        for item in values:
            for part in item.split(','):
                matches = glob.glob(part)
                expanded.extend(matches if matches else [part])
        setattr(namespace, self.dest, expanded)


def main() -> None:
    """
    Main CLI dispatch function for the GONet Wizard package.

    Parses user input from the command line and delegates to the appropriate
    command module. Supports both top-level and nested subcommands.

    Returns
    -------
    None
    """

    parser = argparse.ArgumentParser(
        description="GONet Wizard command-line interface."
    )
    
    parser.add_argument('--version', action='version', version=f"GONet Wizard {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Top-level commands")

    # === Subcommand: show ===
    show_parser = subparsers.add_parser(
        "show", help="Plot the content of one or more GONet files."
    )
    show_parser.add_argument("filenames", nargs='+', action=ExpandFilenames, help="GONet file(s) to plot.")
    show_parser.add_argument("--save", help="Save output as a PDF.")
    show_parser.add_argument("--red", action="store_true", default=False, help="Plot only the red channel.")
    show_parser.add_argument("--green", action="store_true", default=False, help="Plot only the green channel.")
    show_parser.add_argument("--blue", action="store_true", default=False, help="Plot only the blue channel.")

    # === Subcommand: show_meta ===
    meta_parser = subparsers.add_parser(
        "show_meta", help="Print metadata from one or more GONet files."
    )
    meta_parser.add_argument("filenames", nargs='+', action=ExpandFilenames, help="GONet file(s) to inspect.")

    # === Subcommand: dashboard ===
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="Launch the interactive GONet dashboard."
    )

    # === Subcommand group: connect ===
    operate_parser = subparsers.add_parser(
        "connect", help="Connect to a remote GONet device."
    )
    operate_parser.add_argument("gonet_ip", help="IP address of the GONet device.")
    operate_subparsers = operate_parser.add_subparsers(dest="subcommand", required=True)

    # Nested subcommand: snap
    snap_parser = operate_subparsers.add_parser(
        "snap", help="Trigger remote gonet4.py execution with optional config file."
    )
    snap_parser.add_argument("config_file", nargs="?", default=None, help="Optional path to config file.")

    # Nested subcommand: terminate_imaging
    terminate_parser = operate_subparsers.add_parser(
        "terminate_imaging", help="Terminate remote imaging (clear crontab, kill processes)."
    )

    # === Subcommand: extract ===
    extract_parser = subparsers.add_parser(
        "extract", help="Extract counts from a region one or more GONet files."
    )
    extract_parser.add_argument("filenames", nargs='+', action=ExpandFilenames, help="GONet file(s) to extract. `*` wildcards and comma-separated lists are supported.")

    extract_parser.add_argument("--red", action="store_true", default=False, help="Extract only the red channel.")
    extract_parser.add_argument("--green", action="store_true", default=False, help="Extract only the green channel.")
    extract_parser.add_argument("--blue", action="store_true", default=False, help="Extract only the blue channel.")

    extract_parser.add_argument("--shape", choices=["circle", "rectangle", "annulus", "interactive"], help="Shape of the extraction region.  If shape is 'interactive', or no shape is parsed, the user will select the region interactively.")
    extract_parser.add_argument("--center", help="Center of the region in pixels, as 2 comma-separated values: x,y. Example: 1000,800")
    extract_parser.add_argument("--radius", help="Radius in pixels (required if shape is circle).")
    extract_parser.add_argument("--sides", help="Sides in pixels, as 2 comma-separated values: x,y. width,height (required if shape is rectangle). Example: 300,400")
    extract_parser.add_argument("--inner_radius", help="Inner radius in pixels. (required if shape is annulus).")
    extract_parser.add_argument("--outer_radius", help="Outer radius in pixels (required if shape is annulus).")
    extract_parser.add_argument("--angles", help="Angles in degrees, as 2 comma-separated values: start_angle,end_angle (optional). 0 degrees is along the +x axis, and angles increase counter-clockwise. Example: -120,120", default="-180,180")
    extract_parser.add_argument("--output", help="Output JSON file name. Default name is 'extraction_shape.json'. If files already exists, it will not be overwritten, but a new file will be created with sequential number added to it.")


    # === Dispatch logic ===
    args = parser.parse_args()

    if args.command == "show":
        commands.show_gonet_files(args.filenames, args.save, args.red, args.green, args.blue)
    elif args.command == "show_meta":
        commands.show_metadata(args.filenames)
    elif args.command == "dashboard":
        commands.run()
    elif args.command == "connect":
        if args.subcommand == "snap":
            commands.take_snapshot(args.gonet_ip, args.config_file)
        elif args.subcommand == "terminate_imaging":
            commands.terminate_imaging(args.gonet_ip)
    elif args.command == 'extract':
        commands.extract_counts_from_GONet(args.filenames, args.red, args.green, args.blue, args.shape, args.center, args.radius, args.sides, args.inner_radius, args.outer_radius, args.angles, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
