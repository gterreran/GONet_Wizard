# GONet_Wizard/__main__.py

"""
Module entry point for `python -m GONet_Wizard` and the console script.

This file simply re-exports :func:`GONet_Wizard.cli.main` as ``main`` and
invokes it when run as a script.
"""

from GONet_Wizard import cli as _cli


def main(argv=None) -> None:
    """
    Delegate to :func:`GONet_Wizard.cli.main`.

    Parameters
    ----------
    argv : list of str, optional
        Optional argument vector to pass to the CLI. When None, ``sys.argv[1:]``
        is used, matching standard command-line behavior.
    """
    _cli.main(argv)


if __name__ == "__main__":
    main()
