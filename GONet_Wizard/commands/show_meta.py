"""
Display Metadata from GONet Files.

This script provides a simple command-line tool to extract and display
metadata from one or more GONet file paths.

**Functions**

- :func:`show_meta` : Display the metadata content of one or more GONet files.

"""

from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from typing import Union, List
import pprint, os


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

