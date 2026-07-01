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
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Union

from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.commands.cli_core import CommandSpec, ExpandFilenames, filter_by_ext
from GONet_Wizard.commands.show_meta_session import ShowMetaSession, show_meta_session_registry


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



def _ensure_pdf_extension(save_path: str) -> str:
    """Return ``save_path`` with a ``.pdf`` suffix if no suffix was provided."""
    root, ext = os.path.splitext(save_path)
    if ext.lower() != ".pdf":
        return save_path + ".pdf" if not ext else root + ".pdf"
    return save_path


def _avoid_overwrite(save_path: str) -> str:
    """Return a non-existing path by adding a numeric suffix if necessary."""
    final_path = _ensure_pdf_extension(save_path)
    base, ext = os.path.splitext(final_path)
    counter = 1
    while os.path.exists(final_path):
        final_path = f"{base}_{counter}{ext}"
        counter += 1
    return final_path


def _flatten_metadata_rows(value: object, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten nested metadata into ``(key, value)`` rows suitable for PDF tables."""
    rows: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            child_prefix = f"{prefix}.{key_text}" if prefix else key_text
            rows.extend(_flatten_metadata_rows(item, child_prefix))
        return rows
    if isinstance(value, (list, tuple)):
        if all(_is_primitive(item) for item in value):
            rows.append((prefix or "value", pprint.pformat(list(value), width=100)))
        else:
            for idx, item in enumerate(value):
                child_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
                rows.extend(_flatten_metadata_rows(item, child_prefix))
        return rows
    rows.append((prefix or "value", pprint.pformat(value, width=100)))
    return rows


def save_metadata_pdf(files: Union[str, Sequence[str]], save_path: str) -> str:
    """Save the metadata shown by ``show_meta`` to a PDF file.

    Parameters
    ----------
    files : :class:`str` or sequence of :class:`str`
        Input GONet files whose metadata should be written.
    save_path : :class:`str`
        Requested PDF output path. ``.pdf`` is added automatically when omitted.

    Returns
    -------
    :class:`str`
        Final path written to disk.

    Raises
    ------
    :class:`RuntimeError`
        If the ReportLab PDF backend is unavailable or the PDF cannot be written.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape as xml_escape
    except Exception as exc:  # pragma: no cover - exercised only without dependency
        raise RuntimeError(
            "Saving show_meta output to PDF requires the 'reportlab' package. "
            "Try: pip install -U reportlab"
        ) from exc

    if isinstance(files, str):
        files_list = [files]
    else:
        files_list = list(files)

    final_path = _avoid_overwrite(str(save_path))
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 8
    body.leading = 10

    story = [Paragraph("GONet metadata", styles["Title"]), Spacer(1, 12)]

    for path in files_list:
        story.append(Paragraph(f"File: {xml_escape(str(path))}", styles["Heading2"]))
        try:
            go = GONetFile.from_file(path)
            if not os.path.isfile(path):
                rows = [("Status", "File does not exist.")]
            elif getattr(go, "meta", None) is None:
                rows = [("Status", "No metadata associated with this file.")]
            else:
                rows = _flatten_metadata_rows(go.meta)
                if not rows:
                    rows = [("Status", "Metadata is empty.")]
        except Exception as exc:
            rows = [("Error", f"Error reading metadata: {exc}")]

        table_data = [[Paragraph("Key", body), Paragraph("Value", body)]]
        for key, value in rows:
            table_data.append([
                Paragraph(xml_escape(str(key)), body),
                Paragraph(xml_escape(str(value)).replace("\n", "<br/>") , body),
            ])

        table = Table(table_data, colWidths=[180, 340], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#999999")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.extend([table, Spacer(1, 12)])

    try:
        SimpleDocTemplate(
            final_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        ).build(story)
    except Exception as exc:
        raise RuntimeError(f"Failed to write metadata PDF: {exc}") from exc

    return final_path


def _append_interactive_actions(html_output: str, session_id: str) -> str:
    """Append Save PDF and Exit buttons to the interactive metadata HTML."""
    close_url = f"/show_meta/session/{session_id}/close"
    return f"""
{html_output}
<div class="gw-controls-row" style="justify-content: flex-end; margin-top: 10px;">
  <div class="gw-controls" role="group" aria-label="Show metadata actions">
    <button type="button" id="gw-save-meta-btn">Save PDF</button>
    <button type="button" id="gw-exit-meta-btn">Exit</button>
  </div>
</div>
<script>
(function() {{
  const closeUrl = {close_url!r};
  let actionSubmitted = false;

  function postClose(savePath) {{
    if (actionSubmitted) return;
    actionSubmitted = true;
    fetch(closeUrl, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ save_path: savePath || '' }}),
      keepalive: true,
    }}).catch(() => {{}});
  }}

  function closeMetaWindow() {{
    try {{
      window.parent && window.parent.postMessage({{ type: 'gonet-close-window', key: 'show_meta' }}, '*');
    }} catch (err) {{}}
    try {{
      if (window.pywebview && window.pywebview.api) {{
        if (typeof window.pywebview.api.close_named_window === 'function') {{
          window.pywebview.api.close_named_window('show_meta');
          return;
        }}
        if (typeof window.pywebview.api.close_window === 'function') {{
          window.pywebview.api.close_window();
          return;
        }}
      }}
    }} catch (err) {{}}
    window.close();
  }}

  async function handleSave() {{
    if (actionSubmitted) return;
    let savePath = '';
    try {{
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.pick_save_path === 'function') {{
        savePath = await window.pywebview.api.pick_save_path('gonet_metadata.pdf');
      }} else {{
        savePath = window.prompt('Save metadata PDF as', 'gonet_metadata.pdf') || '';
      }}
    }} catch (err) {{
      savePath = '';
    }}
    if (!savePath) return;
    postClose(savePath);
    closeMetaWindow();
  }}

  function handleExit() {{
    if (actionSubmitted) return;
    postClose('');
    closeMetaWindow();
  }}

  document.getElementById('gw-save-meta-btn').addEventListener('click', handleSave);
  document.getElementById('gw-exit-meta-btn').addEventListener('click', handleExit);
}})();
</script>
"""

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

    as_html = bool(getattr(args, "html", False))
    output = show_metadata(files, as_html=as_html)

    if as_html:
        session_id = uuid.uuid4().hex
        show_meta_session_registry.register(
            ShowMetaSession(
                session_id=session_id,
                files=[str(path) for path in files],
                terminal_stream=getattr(args, "_gonet_terminal_stream", None),
            )
        )
        return _append_interactive_actions(output, session_id)

    print(output)
    return None
