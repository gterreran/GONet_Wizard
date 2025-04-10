# MyPackage/__main__.py
import argparse
from GONet_Wizard import GONet_dashboard, GONet_utils

def main():
    parser = argparse.ArgumentParser(description="MyPackage command-line interface.")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: show
    show_parser = subparsers.add_parser("show", help="Plot the content of one or multiple GONet files.")
    show_parser.add_argument("filenames", nargs='+', help='GONet files.')
    show_parser.add_argument("--save", help='Save output to pdf.')
    show_parser.add_argument("--red", help='Load only red components.', action='store_true', default=False)
    show_parser.add_argument("--green", help='Load only green components.', action='store_true', default=False)
    show_parser.add_argument("--blue", help='Load only blue components.', action='store_true', default=False)

    # Subcommand: show_meta
    show_parser = subparsers.add_parser("show_meta", help="Show the meta data of one of multiple GONet files.")
    show_parser.add_argument("filenames", nargs='+', help='GONet files.')

    # Subcommand: run_dashboard
    dashboard_parser = subparsers.add_parser("dashboard", help="Run the dashboard.")

    # First-level command: operate
    operate_parser = subparsers.add_parser("connect", help="Connect to a remote camera")
    operate_parser.add_argument("gonet_ip", help="IP address of the camera")
    operate_subparsers = operate_parser.add_subparsers(dest="subcommand", required=True)

    # Nested command: snap
    snap_parser = operate_subparsers.add_parser("snap", help="Run gonet4.py remotely, using a local config file.")
    snap_parser.add_argument("config_file", help="Configuration file for snapshot")

    # Nested command: terminate imaging
    terminate_parser = operate_subparsers.add_parser("terminate_imaging", help="Clear the crontab, terminating and automated imaging")

    args = parser.parse_args()

    if args.command == "show":
        GONet_utils.show(args.filenames, args.save, args.red, args.green, args.blue)
    elif args.command == "show_meta":
        GONet_utils.show_meta(args.filenames)
    elif args.command == "dashboard":
        GONet_dashboard.run()
    elif args.command == "connect":
        if args.subcommand == "snap":
            GONet_utils.snap(args.gonet_ip, args.config_file)
        if args.subcommand == "terminate_imaging":
            GONet_utils.terminate_imaging(args.gonet_ip)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()