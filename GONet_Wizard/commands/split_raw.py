"""
CLI command for splitting RAW GONet JPEG files into standard images.

The ``split_raw`` command reads one or more original GONet RAW ``.jpg`` files
and writes standard image products next to each input by default:

- a 16-bit TIFF file (``<stem>.tiff``), and
- a standard 8-bit JPEG file (``<stem>.jpeg``).

When an output directory is supplied, the command keeps products organized in
separate ``tiffs`` and ``jpegs`` subdirectories. TIFF products do not apply white
balance by default so their pixel values remain as faithful as possible to the
RAW data for scientific extraction. JPEG products keep white balance enabled by
default because they are usually intended for visual inspection.

The image loading and writing are delegated to
:class:`GONet_Wizard.GONet_utils.GONetFile`, which already knows how to parse
GONet RAW JPEG files and export the processed RGB channels. This module keeps
the command-layer behavior focused on CLI/GUI arguments, path handling, and
safe overwrite checks.

Constants
---------
:data:`COMMAND`
    Declarative command specification used by the shared parser builder and GUI
    form generator.

Functions
---------
:func:`output_paths_for_raw`
    Resolve the TIFF and JPEG output paths for one input file.
:func:`split_raw_file`
    Convert a single RAW input file into the requested output products.
:func:`split_raw_files`
    Convert a sequence of RAW input files.
:func:`cli_handler`
    Execute the command after argparse has populated the namespace.
"""

from __future__ import annotations

import argparse
from collections import namedtuple
from pathlib import Path
from typing import Iterable, Literal

from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.commands.cli_core import CommandSpec, ExpandFilenames, filter_by_ext

OutputFormat = Literal["both", "tiff", "jpeg"]


class SplitRawOutput(namedtuple("_SplitRawOutput", ["input_file", "tiff", "jpeg"])):
    """Small return container for paths written by one conversion."""

    __slots__ = ()


COMMAND = CommandSpec(
    name="split_raw",
    help="Convert RAW GONet .jpg files into standard TIFF and JPEG images.",
    args=[
        {
            "flags": ["input"],
            "nargs": "+",
            "action": ExpandFilenames,
            "help": (
                "Input GONet RAW (*.jpg) file(s), folder(s), glob(s), "
                "or comma-separated lists."
            ),
        },
        {
            "flags": ["--outdir"],
            "type": str,
            "default": None,
            "help": (
                "Optional output directory. When set, TIFF and JPEG products "
                "are written under tiffs/ and jpegs/ subfolders. Defaults to "
                "writing next to each input file."
            ),
        },
        {
            "flags": ["--format"],
            "choices": ["both", "tiff", "jpeg"],
            "default": "both",
            "help": "Output product(s) to write. Default: both.",
        },
        {
            "flags": ["--overwrite"],
            "action": "store_true",
            "default": False,
            "help": "Overwrite existing output files.",
        },
        {
            "flags": ["--tiff-white-balance"],
            "action": "store_true",
            "default": False,
            "help": (
                "Apply metadata white-balance gains to TIFF outputs. Disabled "
                "by default to preserve raw-like pixel counts for extraction."
            ),
        },
        {
            "flags": ["--no-jpeg-white-balance"],
            "action": "store_true",
            "default": False,
            "help": (
                "Disable metadata white-balance gains for JPEG outputs. JPEG "
                "white balance is enabled by default."
            ),
        },
    ],
)


def _normalize_format(output_format: str) -> OutputFormat:
    """
    Validate and normalize an output-format string.

    Parameters
    ----------
    output_format : :class:`str`
        Requested output format. Supported values are ``"both"``, ``"tiff"``,
        and ``"jpeg"``.

    Returns
    -------
    :class:`str`
        The normalized output format.

    Raises
    ------
    ValueError
        If ``output_format`` is not supported.
    """
    normalized = str(output_format).lower()
    if normalized not in {"both", "tiff", "jpeg"}:
        raise ValueError(
            "output_format must be one of 'both', 'tiff', or 'jpeg'."
        )
    return normalized  # type: ignore[return-value]


def _product_dir(source: Path, outdir: str | Path | None, product_folder: str) -> Path:
    """
    Resolve the parent directory for one output product kind.

    Parameters
    ----------
    source : :class:`pathlib.Path`
        Source RAW input path.
    outdir : :class:`str` or :class:`pathlib.Path`, optional
        Base output directory. If omitted, outputs stay next to ``source``.
    product_folder : :class:`str`
        Product subfolder name used when ``outdir`` is supplied.

    Returns
    -------
    :class:`pathlib.Path`
        Directory that should contain the requested product.
    """
    if outdir is None:
        return source.parent
    return Path(outdir) / product_folder


def output_paths_for_raw(
    input_file: str | Path,
    outdir: str | Path | None = None,
    output_format: str = "both",
) -> SplitRawOutput:
    """
    Resolve standard TIFF/JPEG output paths for one RAW input file.

    By default, outputs are written next to the input. TIFF outputs use
    ``<stem>.tiff`` and JPEG outputs use ``<stem>.jpeg`` so the generated JPEG
    does not overwrite the source RAW ``.jpg`` file. When ``outdir`` is supplied,
    TIFF outputs are written under ``outdir/tiffs`` and JPEG outputs under
    ``outdir/jpegs``.

    Parameters
    ----------
    input_file : :class:`str` or :class:`pathlib.Path`
        Source RAW GONet JPEG file.
    outdir : :class:`str` or :class:`pathlib.Path`, optional
        Base directory in which outputs should be written. If omitted, the input
        file's parent directory is used.
    output_format : :class:`str`, optional
        Which product(s) to create: ``"both"`` (default), ``"tiff"``, or
        ``"jpeg"``.

    Returns
    -------
    :class:`SplitRawOutput`
        Named tuple containing the source path and requested output paths.
    """
    fmt = _normalize_format(output_format)
    source = Path(input_file)
    stem = source.stem

    return SplitRawOutput(
        input_file=source,
        tiff=(
            _product_dir(source, outdir, "tiffs") / f"{stem}.tiff"
            if fmt in {"both", "tiff"}
            else None
        ),
        jpeg=(
            _product_dir(source, outdir, "jpegs") / f"{stem}.jpeg"
            if fmt in {"both", "jpeg"}
            else None
        ),
    )


def _check_output_paths(paths: SplitRawOutput, overwrite: bool) -> None:
    """
    Validate output paths before writing products.

    Parameters
    ----------
    paths : :class:`SplitRawOutput`
        Resolved output path bundle.
    overwrite : :class:`bool`
        Whether existing outputs may be overwritten.

    Raises
    ------
    FileExistsError
        If an output exists and ``overwrite`` is False.
    ValueError
        If a requested output path would overwrite the input file itself.
    """
    requested = [p for p in (paths.tiff, paths.jpeg) if p is not None]
    source = paths.input_file.resolve()

    for path in requested:
        resolved = path.resolve()
        if resolved == source:
            raise ValueError(f"Refusing to overwrite input file: {path}")
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {path}. Use --overwrite to replace it."
            )


def split_raw_file(
    input_file: str | Path,
    outdir: str | Path | None = None,
    output_format: str = "both",
    overwrite: bool = False,
    tiff_white_balance: bool = False,
    jpeg_white_balance: bool = True,
) -> SplitRawOutput:
    """
    Convert one RAW GONet JPEG file into standard image products.

    Parameters
    ----------
    input_file : :class:`str` or :class:`pathlib.Path`
        Source RAW GONet JPEG file.
    outdir : :class:`str` or :class:`pathlib.Path`, optional
        Base output directory. If omitted, outputs are written next to the
        input. If supplied, products are written under ``tiffs`` and ``jpegs``
        subfolders.
    output_format : :class:`str`, optional
        Which product(s) to create: ``"both"`` (default), ``"tiff"``, or
        ``"jpeg"``.
    overwrite : :class:`bool`, optional
        If True, existing outputs may be replaced. Defaults to False.
    tiff_white_balance : :class:`bool`, optional
        Whether to apply metadata white-balance gains to TIFF outputs. Defaults
        to False so TIFF pixel counts remain close to the RAW data.
    jpeg_white_balance : :class:`bool`, optional
        Whether to apply metadata white-balance gains to JPEG outputs. Defaults
        to True for visually useful JPEG products.

    Returns
    -------
    :class:`SplitRawOutput`
        Paths written for this input file.
    """
    paths = output_paths_for_raw(input_file, outdir=outdir, output_format=output_format)

    if paths.tiff is not None:
        paths.tiff.parent.mkdir(parents=True, exist_ok=True)
    if paths.jpeg is not None:
        paths.jpeg.parent.mkdir(parents=True, exist_ok=True)

    _check_output_paths(paths, overwrite=overwrite)

    gonet_file = GONetFile.from_file(paths.input_file)

    if paths.tiff is not None:
        gonet_file.write_to_tiff(str(paths.tiff), white_balance=tiff_white_balance)
    if paths.jpeg is not None:
        gonet_file.write_to_jpeg(str(paths.jpeg), white_balance=jpeg_white_balance)

    return paths


def split_raw_files(
    input_files: Iterable[str | Path],
    outdir: str | Path | None = None,
    output_format: str = "both",
    overwrite: bool = False,
    tiff_white_balance: bool = False,
    jpeg_white_balance: bool = True,
) -> list[SplitRawOutput]:
    """
    Convert multiple RAW GONet JPEG files into standard image products.

    Parameters
    ----------
    input_files : iterable of :class:`str` or :class:`pathlib.Path`
        Source RAW GONet JPEG files.
    outdir : :class:`str` or :class:`pathlib.Path`, optional
        Base output directory for all products. If omitted, each input's parent
        directory is used. If supplied, products are written under ``tiffs`` and
        ``jpegs`` subfolders.
    output_format : :class:`str`, optional
        Which product(s) to create: ``"both"`` (default), ``"tiff"``, or
        ``"jpeg"``.
    overwrite : :class:`bool`, optional
        If True, existing outputs may be replaced. Defaults to False.
    tiff_white_balance : :class:`bool`, optional
        Whether to apply metadata white-balance gains to TIFF outputs. Defaults
        to False.
    jpeg_white_balance : :class:`bool`, optional
        Whether to apply metadata white-balance gains to JPEG outputs. Defaults
        to True.

    Returns
    -------
    list of :class:`SplitRawOutput`
        Paths written for each input file.
    """
    return [
        split_raw_file(
            input_file,
            outdir=outdir,
            output_format=output_format,
            overwrite=overwrite,
            tiff_white_balance=tiff_white_balance,
            jpeg_white_balance=jpeg_white_balance,
        )
        for input_file in input_files
    ]


def _format_written_paths(outputs: Iterable[SplitRawOutput]) -> str:
    """Return a human-readable summary of written output paths."""
    lines: list[str] = []
    for output in outputs:
        written = [p for p in (output.tiff, output.jpeg) if p is not None]
        lines.append(f"{output.input_file} -> {', '.join(str(p) for p in written)}")
    return "\n".join(lines)


def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler for the ``split_raw`` command.

    The handler prints a terminal-friendly summary and intentionally returns
    ``None``. Returning an HTML-like string would be interpreted by the shared
    CLI UI bridge as a preview request, which would open an unnecessary window
    for this terminal-only conversion command.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments produced from :data:`COMMAND`.

    Returns
    -------
    None
        Feedback is emitted to stdout so both the terminal and GUI fake terminal
        receive the same summary.

    Raises
    ------
    :class:`~GONet_Wizard.commands.inputs.ExtensionFilterError`
        If the supplied inputs do not include supported RAW JPEG files.
    """
    files = filter_by_ext(args.input, [".jpg"])
    outputs = split_raw_files(
        input_files=files,
        outdir=args.outdir,
        output_format=args.format,
        overwrite=bool(args.overwrite),
        tiff_white_balance=bool(args.tiff_white_balance),
        jpeg_white_balance=not bool(args.no_jpeg_white_balance),
    )

    summary = _format_written_paths(outputs)
    if summary:
        print(summary)
    return None
