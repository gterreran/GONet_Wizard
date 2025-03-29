# MyPackage/__main__.py
import argparse
from GONet_Wizard import GONet_dashboard, GONet_utils

def main():
    parser = argparse.ArgumentParser(description="MyPackage command-line interface.")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: show
    show_parser = subparsers.add_parser("show", help="Show the content of a file.")
    show_parser.add_argument("filenames", nargs='+', help='GONet files to be plotted.')
    show_parser.add_argument("--save", help='Save output to pdf.')
    show_parser.add_argument("--red", help='Load only red components.', action='store_true', default=False)
    show_parser.add_argument("--green", help='Load only green components.', action='store_true', default=False)
    show_parser.add_argument("--blue", help='Load only blue components.', action='store_true', default=False)

    # Subcommand: snap
    snap_parser = subparsers.add_parser("snap", help="Run gonet4.py remotely, using a local config file.")
    snap_parser.add_argument("gonet_ip", help="IP address of the GONet to control.")
    snap_parser.add_argument("config_file", help="Path to local config file")

    # Subcommand: run_dashboard
    dashboard_parser = subparsers.add_parser("dashboard", help="Run the dashboard.")

    args = parser.parse_args()

    if args.command == "show":
        GONet_utils.show(args.filenames, args.save, args.red, args.green, args.blue)
    elif args.command == "snap":
        GONet_utils.snap(args.gonet_ip, args.config_file)
    elif args.command == "dashboard":
        GONet_dashboard.run()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()