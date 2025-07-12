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

"""



import argparse
from GONet_Wizard import commands
from GONet_Wizard._version import __version__


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
        "show", help="Plot the content of one or more GONet .npy files."
    )
    show_parser.add_argument("filenames", nargs='+', help="GONet file(s) to plot.")
    show_parser.add_argument("--save", help="Save output as a PDF.")
    show_parser.add_argument("--red", action="store_true", default=False, help="Plot only the red channel.")
    show_parser.add_argument("--green", action="store_true", default=False, help="Plot only the green channel.")
    show_parser.add_argument("--blue", action="store_true", default=False, help="Plot only the blue channel.")

    # === Subcommand: show_meta ===
    meta_parser = subparsers.add_parser(
        "show_meta", help="Print metadata from one or more GONet files."
    )
    meta_parser.add_argument("filenames", nargs='+', help="GONet file(s) to inspect.")

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
