"""
GONet Metadata Display Command
===============================

Display Metadata from GONet Files.

This script provides a simple command-line tool to extract and display
metadata from one or more GONet file paths. The command is declared via
the :data:`COMMAND` constant, which specifies the argument structure used by
the centralized parser builder.

**Constants**

- :data:`COMMAND` : :class:`~GONet_Wizard.commands.cli_core.CommandSpec` object
  for the `show_meta` command.

**Functions**

- :func:`show_meta` : Display the metadata content of one or more GONet files.

"""

from GONet_Wizard.GONet_utils import GONetFile
from typing import Union, List
import pprint, os, argparse
from GONet_Wizard.commands.cli_core import ExpandFilenames, CommandSpec, filter_by_ext

COMMAND = CommandSpec(
    name="show_meta",
    help="Print metadata from one or more GONet files.",
    args=[
        {
            "flags": ["filenames"],
            "nargs": "+",
            "action": ExpandFilenames,
            "help": "GONet file(s) to inspect [.jpg, .tiff]. `*` wildcards and comma-separated lists are supported."
        }
    ]
)


def show_metadata(files: Union[str, List[str]]) -> None:
    """
    Display the metadata content of one or more GONet files.

    This function extracts the metadata from GONet file(s), and
    pretty-prints them to the console. If the file(s) does
    not exist or cannot be parsed, a warning is shown instead.

    Parameters
    ----------
    files : :class:`str` or :class:`list` of :class:`str`
        A single file path or a list of file paths pointing to GONet files.

    Returns
    -------
    None

    Notes
    -----
    - This function is typically used as a CLI utility via the `commands/` interface.
    - The output is printed using :mod:`pprint` for readability.
    """
    if isinstance(files, str):
        files = [files]

    for path in files:
        print(f"\n📂 File: {path}")
        if not os.path.isfile(path):
            print("   ❌ File does not exist.")
            continue

        try:
            go = GONetFile.from_file(path)
            if go.meta is None:
                print("   ℹ️ No metadata associated with this file.")
            else:
                print("🧾 Metadata:")
                pprint.pprint(go.meta, indent=4, width=100)
        except Exception as e:
            print(f"   ⚠️ Error reading metadata: {e}")


def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler for the `show_meta` command.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments.
    
    Returns
    -------
    None
    
    """
    files = filter_by_ext(args.filenames, [".jpg", ".tiff"])
    show_metadata(
        files=files,
    )