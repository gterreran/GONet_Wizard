# MyPackage/__main__.py
import argparse
from GONet_Wizard import GONet_dashboard, GONet_utils

def main():
    parser = argparse.ArgumentParser(description="MyPackage command-line interface.")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: show
    show_parser = subparsers.add_parser("show", help="Show the content of a file.")
    show_parser.add_argument("filename", help="The file to show.")

    # Subcommand: run_dashboard
    subparsers.add_parser("dashboard", help="Run the dashboard.")

    args = parser.parse_args()

    if args.command == "show":
        GONet_utils.show(args.filename)
    elif args.command == "dashboard":
        GONet_dashboard.run()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()