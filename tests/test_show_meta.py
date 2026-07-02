from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_show_meta_html_adds_save_pdf_and_exit_actions(monkeypatch):
    from GONet_Wizard.commands import show_meta

    monkeypatch.setattr(show_meta, "filter_by_ext", lambda files, exts: [Path("image.jpg")])
    monkeypatch.setattr(show_meta, "show_metadata", lambda files, as_html=False: "<div>metadata</div>")

    args = SimpleNamespace(filenames=[Path("image.jpg")], html=True)
    html = show_meta.cli_handler(args)

    assert "metadata" in html
    assert "gw-save-meta-btn" in html
    assert "gw-exit-meta-btn" in html
    assert "Save PDF" in html
    assert "Exit" in html
    assert "/show_meta/session/" in html
    assert "gonet-pick-save-path" in html
    assert "metadataSaveFileTypes" in html
    assert "PDF files (*.pdf)" in html
    assert "window.prompt" not in html
    assert "setTimeout" not in html


def test_save_metadata_pdf_adds_pdf_extension_and_avoids_overwrite(monkeypatch, tmp_path):
    from GONet_Wizard.commands import show_meta

    class DummyGONetFile:
        meta = {"camera": "GONet", "values": [1, 2, 3]}

    monkeypatch.setattr(show_meta.GONetFile, "from_file", staticmethod(lambda path: DummyGONetFile()))
    monkeypatch.setattr(show_meta.os.path, "isfile", lambda path: True)

    existing = tmp_path / "metadata.pdf"
    existing.write_text("existing", encoding="utf-8")

    out = show_meta.save_metadata_pdf(["image.jpg"], str(tmp_path / "metadata"))

    assert out == str(tmp_path / "metadata_1.pdf")
    assert Path(out).exists()
