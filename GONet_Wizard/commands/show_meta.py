# GONet_Wizard/commands/show_meta.py

"""
GONet Metadata Display Command
==============================

This module implements the ``show_meta`` CLI command, which extracts and displays
metadata from one or more GONet image files. Output can be rendered either as
plain text (for terminal use) or as HTML suitable for display in GUI contexts.

The command is declared via the :data:`COMMAND` specification and dispatched
through :func:`cli_handler`. Core formatting is handled by :func:`show_metadata`,
which returns a rendered string without printing so callers can decide how to
present the result.

Constants
---------
:class:`COMMAND`
    :class:`~GONet_Wizard.commands.specs.CommandSpec` defining the ``show_meta`` command.

Classes
-------
:class:`._EmitBuffer`
    Internal line buffer that renders accumulated output as text or HTML.

Functions
---------
:func:`show_metadata`
    Extract and format metadata for one or more GONet files as text or HTML.
:func:`cli_handler`
    CLI entry point for ``show_meta``.
:func:`_render_value_html`
    Render a Python value as HTML, recursively formatting containers.
:func:`_dict_to_table`
    Render a mapping as an HTML table.
:func:`_list_to_table`
    Render a list/sequence as inline HTML or a table, depending on content.

"""

from __future__ import annotations

import argparse
import html
import os
import pprint
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Union

from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.commands.cli_core import CommandSpec, ExpandFilenames, filter_by_ext


COMMAND = CommandSpec(
    name="show_meta",
    help="Print metadata from one or more GONet files.",
    args=[
        {
            "flags": ["filenames"],
            "nargs": "+",
            "action": ExpandFilenames,
            "help": (
                "GONet file(s) to inspect [.jpg, .tiff]. "
                "`*` wildcards and comma-separated lists are supported."
            ),
        },
        {
            "flags": ["--html"],
            "action": "store_true",
            "help": "Return output as an HTML string instead of printing to terminal.",
        },
    ],
)


@dataclass
class _EmitBuffer:
    """
    Collect output lines and render them as console text or HTML.

    Attributes
    ----------
    mode : :class:`str`
        Output mode. Must be ``"text"`` or ``"html"``.
    _lines : :class:`list` of :class:`str`
        Accumulated output lines.
    """

    mode: str = "text"
    _lines: List[str] = field(default_factory=list)

    def line(self, s: str = "") -> None:
        """
        Append one line to the output buffer.

        Parameters
        ----------
        s : :class:`str`, optional
            Line to append. Defaults to an empty string.

        Returns
        -------
        None
        """
        self._lines.append(s)

    def text(self) -> str:
        """
        Render the buffer as plain text.

        Returns
        -------
        :class:`str`
            Text output constructed by joining lines with newlines.
        """
        return "\n".join(self._lines)

    def html(self) -> str:
        """
        Render the buffer as an HTML fragment.

        Returns
        -------
        :class:`str`
            HTML output containing the accumulated lines.
        """
        return "<div class='meta-output'>\n" + "\n".join(self._lines) + "\n</div>\n"

    def render(self) -> str:
        """
        Render the buffer in the selected mode.

        Returns
        -------
        :class:`str`
            Rendered output as either text or HTML depending on :attr:`mode`.

        Raises
        ------
        ValueError
            If :attr:`mode` is not ``"text"`` or ``"html"``.
        """
        if self.mode == "html":
            return self.html()
        if self.mode == "text":
            return self.text()
        raise ValueError(f"Unknown output mode: {self.mode!r}")


def _is_primitive(x: object) -> bool:
    """
    Test whether a value should be displayed as a primitive scalar.

    Parameters
    ----------
    x : :class:`object`
        Value to test.

    Returns
    -------
    :class:`bool`
        ``True`` if the value is ``None`` or an instance of :class:`str`,
        :class:`int`, :class:`float`, or :class:`bool`.
    """
    return x is None or isinstance(x, (str, int, float, bool))


def _to_str(x: object) -> str:
    """
    Convert a value to a display string.

    Parameters
    ----------
    x : :class:`object`
        Value to convert.

    Returns
    -------
    :class:`str`
        String representation of ``x``.
    """
    # Keep strings as-is, but stringify other primitives
    return str(x)


def _render_value_html(v: object) -> str:
    """
    Render a Python value as HTML.

    Container types are formatted recursively into HTML tables, while primitive
    values are escaped and styled for inline display.

    Parameters
    ----------
    v : :class:`object`
        Value to render.

    Returns
    -------
    :class:`str`
        HTML representation of the value.
    """
    if isinstance(v, dict):
        return _dict_to_table(v)
    if isinstance(v, (list, tuple)):
        return _list_to_table(list(v))
    if _is_primitive(v):
        return f"<span class='meta-primitive'>{html.escape(_to_str(v))}</span>"
    # Fallback for weird types (bytes, datetime, objects...)
    return f"<code class='meta-code'>{html.escape(repr(v))}</code>"


def _dict_to_table(d: dict) -> str:
    """
    Render a mapping as an HTML table.

    Parameters
    ----------
    d : :class:`dict`
        Mapping of keys to values to render.

    Returns
    -------
    :class:`str`
        HTML table representing the mapping.
    """
    rows = []
    for k, v in d.items():
        key_html = html.escape(str(k))
        val_html = _render_value_html(v)
        rows.append(
            "<tr>"
            f"<th class='meta-key'>{key_html}</th>"
            f"<td class='meta-val'>{val_html}</td>"
            "</tr>"
        )
    return "<table class='meta-table'>" + "".join(rows) + "</table>"


def _list_to_table(items: list) -> str:
    """
    Render a list of values as HTML.

    Short lists of primitive values are rendered inline. Longer or structured
    lists are rendered as indexed tables.

    Parameters
    ----------
    items : :class:`list`
        List of values to render.

    Returns
    -------
    :class:`str`
        HTML representation of the list.
    """
    # If it's a short list of primitives, show it inline
    if all(_is_primitive(x) for x in items) and len(items) <= 12:
        parts = ", ".join(html.escape(_to_str(x)) for x in items)
        return f"<span class='meta-list-inline'>[{parts}]</span>"

    # Otherwise render as an indexed table
    rows = []
    for i, v in enumerate(items):
        rows.append(
            "<tr>"
            f"<th class='meta-key'>[{i}]</th>"
            f"<td class='meta-val'>{_render_value_html(v)}</td>"
            "</tr>"
        )
    return "<table class='meta-table meta-list'>" + "".join(rows) + "</table>"


def show_metadata(
    files: Union[str, Sequence[str]],
    *,
    as_html: bool = False,
    pprint_indent: int = 4,
    pprint_width: int = 100,
) -> str:
    """
    Extract and format metadata for one or more GONet files.

    This function performs no printing. It returns a rendered string (text or
    HTML) so that callers may choose to print it, display it in a UI, or write
    it to disk.

    Parameters
    ----------
    files : :class:`str` or :class:`~collections.abc.Sequence` of :class:`str`
        A single file path or a sequence of file paths pointing to GONet files.
    as_html : :class:`bool`, optional
        If ``True``, return the output as HTML. Defaults to ``False``.
    pprint_indent : :class:`int`, optional
        Indentation passed to :func:`pprint.pformat`. Defaults to ``4``.
    pprint_width : :class:`int`, optional
        Width passed to :func:`pprint.pformat`. Defaults to ``100``.

    Returns
    -------
    :class:`str`
        Rendered output as a string (text by default, HTML if ``as_html=True``).

    Raises
    ------
    ValueError
        If ``files`` is empty.
    """
    if isinstance(files, str):
        files_list = [files]
    else:
        files_list = list(files)

    if not files_list:
        raise ValueError("No files provided to show_metadata().")

    emit = _EmitBuffer(mode="html" if as_html else "text")

    for path in files_list:

        try:
            go = GONetFile.from_file(path)

            if as_html:
                emit.line("<div class='meta-file'>")
                emit.line(
                    f"<div class='meta-file-title'>📂 File: {html.escape(str(path))}</div>"
                )

                if not os.path.isfile(path):
                    emit.line("<div class='meta-note'>❌ File does not exist.</div>")

                elif getattr(go, "meta", None) is None:
                    emit.line(
                        "<div class='meta-note'>ℹ️ No metadata associated with this file.</div>"
                    )
                else:
                    emit.line("<div class='meta-section-title'>🧾 Metadata</div>")
                    emit.line(_dict_to_table(go.meta))

                emit.line("</div>")  # .meta-file
            else:
                if not os.path.isfile(path):
                    emit.line("   ❌ File does not exist.")
                    continue

                if getattr(go, "meta", None) is None:
                    emit.line("   ℹ️ No metadata associated with this file.")
                    continue

                emit.line(f"\n📂 File: {path}")
                emit.line("🧾 Metadata:")

                formatted = pprint.pformat(
                    go.meta, indent=pprint_indent, width=pprint_width
                )
                emit.line(formatted)

        except Exception as e:
            emit.line(f"   ⚠️ Error reading metadata: {e}")

    return emit.render()


def cli_handler(args: argparse.Namespace) -> Optional[str]:
    """
    CLI handler for the ``show_meta`` command.

    This handler filters the provided inputs to supported file types and calls
    :func:`show_metadata`. If ``--html`` is set, it returns the rendered HTML
    string so a higher-level UI wrapper can capture it; otherwise it prints the
    text output to stdout.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments. Expected to provide ``filenames`` and an
        optional ``html`` flag.

    Returns
    -------
    :class:`str` or None
        Rendered HTML string if ``--html`` is set; otherwise ``None`` after
        printing text output.

    Raises
    ------
    :class:`.ExtensionFilterError`
        If none of the provided paths match the supported extensions.
    """
    files = filter_by_ext(args.filenames, [".jpg", ".tiff"])

    output = show_metadata(files, as_html=bool(getattr(args, "html", False)))

    if getattr(args, "html", False):
        return output

    print(output)
    return None
