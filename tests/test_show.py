from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import numpy as np

import pytest

import plotly.graph_objects as go


@dataclass
class DummyArgs:
    filenames: list[Path]
    blue: bool = False
    green: bool = False
    red: bool = False
    window_width_px: int | None = None
    window_height_px: int | None = None


@pytest.fixture
def minimal_css(tmp_path: Path) -> Path:
    """
    Create a minimal STATIC/css/style.css file layout expected by command.py.
    """
    css_dir = tmp_path / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    css_path = css_dir / "style.css"
    css_path.write_text(
        """
:root { --accent-color: rgb(158,248,253); --accent-color-transparent: rgba(158,248,253,0.12); }
body { background: #1a1a1a; color: #f0f0f0; }
.gw-controls-row { display: flex; gap: 12px; align-items: center; margin: 20px; }
.gw-channel-label { color: var(--accent-color); font-weight: 700; }
""".strip(),
        encoding="utf-8",
    )
    return tmp_path


def _dummy_fig(*, rows: int, cols: int, per_file_rows: bool, height: int = 777):
    """
    Produce a minimal object that behaves like a Plotly Figure for command.py.
    We only need `.layout.height` and `.layout.meta`.
    """
    return SimpleNamespace(
        layout=SimpleNamespace(
            height=height,
            meta={"show": {"rows": rows, "cols": cols, "per_file_rows": per_file_rows}},
        )
    )


def test__int_or_default():
    from GONet_Wizard.commands.show.command import _int_or_default

    assert _int_or_default(None, 10) == 10
    assert _int_or_default("12", 10) == 12
    assert _int_or_default("-1", 10) == 10
    assert _int_or_default("nope", 10) == 10


def test__resolve_channels_default_all():
    from GONet_Wizard.commands.show.command import _resolve_channels
    from GONet_Wizard.GONet_utils import GONetFile

    got = _resolve_channels(blue=False, green=False, red=False)
    assert got == list(GONetFile.CHANNELS)


def test__resolve_channels_subset_order():
    from GONet_Wizard.commands.show.command import _resolve_channels
    from GONet_Wizard.GONet_utils import GONetFile

    got = _resolve_channels(blue=True, green=False, red=True)
    expected = [c for c in GONetFile.CHANNELS if c in {"blue", "red"}]
    assert got == expected


def test_cli_handler_requires_css(monkeypatch, tmp_path: Path):
    """
    If STATIC/css/style.css does not exist, cli_handler should raise FileNotFoundError.
    """
    from GONet_Wizard.commands.show import command as show_command
    import GONet_Wizard.settings as settings

    # Ensure the temp STATIC has no css/style.css
    missing_css = tmp_path / "css" / "style.css"
    assert not missing_css.exists()

    # Patch show_command.STATIC (this is what the in-function import reads)
    monkeypatch.setattr(show_command, "STATIC", tmp_path)

    # Avoid real Plotly/figure work
    monkeypatch.setattr(
        show_command,
        "build_show_figure",
        lambda *a, **k: _dummy_fig(rows=1, cols=1, per_file_rows=False),
    )
    monkeypatch.setattr(
        show_command.pio,
        "to_html",
        lambda *a, **k: "<div id='gonet-show-plot'></div>",
    )

    args = SimpleNamespace(
        filenames=[tmp_path / "a.jpg"],
        blue=False,
        green=False,
        red=False,
        window_width_px=1250,
        window_height_px=800,
    )

    with pytest.raises(FileNotFoundError):
        show_command.cli_handler(args)


def test_cli_handler_single_channel_includes_channel_label(monkeypatch, minimal_css: Path):
    """
    When exactly one channel is selected, the HTML should include a channel label.
    """
    from GONet_Wizard.commands.show import command as show_command

    # Patch STATIC to the fixture dir that contains css/style.css
    monkeypatch.setattr("GONet_Wizard.settings.STATIC", minimal_css, raising=False)

    # Avoid real Plotly figure build and HTML generation; focus on cli_handler behavior.
    monkeypatch.setattr(show_command, "build_show_figure", lambda *a, **k: _dummy_fig(rows=2, cols=2, per_file_rows=False, height=555))
    monkeypatch.setattr(show_command.pio, "to_html", lambda *a, **k: "<div id='gonet-show-plot'>PLOT</div>")

    args = SimpleNamespace(
        filenames=[Path("x.jpg")],
        blue=True,
        green=False,
        red=False,
        window_width_px=1200,
        window_height_px=700,
    )

    html = show_command.cli_handler(args)
    assert "Zoom mode" in html
    assert "gonet-show-plot" in html
    assert "Channel:" in html
    assert "Blue" in html  # from channel label


def test_cli_handler_multi_channel_omits_channel_label(monkeypatch, minimal_css: Path):
    from GONet_Wizard.commands.show import command as show_command

    monkeypatch.setattr("GONet_Wizard.settings.STATIC", minimal_css, raising=False)
    monkeypatch.setattr(show_command, "build_show_figure", lambda *a, **k: _dummy_fig(rows=1, cols=3, per_file_rows=True))
    monkeypatch.setattr(show_command.pio, "to_html", lambda *a, **k: "<div id='gonet-show-plot'>PLOT</div>")

    args = SimpleNamespace(
        filenames=[Path("x.jpg")],
        blue=True,
        green=True,
        red=True,
        window_width_px=1200,
        window_height_px=700,
    )

    html = show_command.cli_handler(args)
    assert "Channel:" not in html


def test_cli_handler_uses_figure_meta_to_build_payloads(monkeypatch, minimal_css: Path):
    """
    Verify cli_handler reads layout.meta['show'] and uses it for build_zoom_payloads().
    """
    from GONet_Wizard.commands.show import command as show_command

    monkeypatch.setattr("GONet_Wizard.settings.STATIC", minimal_css, raising=False)
    monkeypatch.setattr(show_command, "build_show_figure", lambda *a, **k: _dummy_fig(rows=3, cols=2, per_file_rows=True))

    monkeypatch.setattr(show_command.pio, "to_html", lambda *a, **k: "<div id='gonet-show-plot'>PLOT</div>")

    called = {}

    def spy_build_zoom_payloads(*, rows: int, cols: int, per_file_rows: bool):
        called["rows"] = rows
        called["cols"] = cols
        called["per_file_rows"] = per_file_rows
        return {"all": {}, "file": {}, "none": {}}

    monkeypatch.setattr(show_command, "build_zoom_payloads", spy_build_zoom_payloads)

    args = SimpleNamespace(
        filenames=[Path("x.jpg")],
        blue=False,
        green=False,
        red=False,
        window_width_px=1200,
        window_height_px=700,
    )

    _ = show_command.cli_handler(args)
    assert called == {"rows": 3, "cols": 2, "per_file_rows": True}



def test_cli_handler_includes_explicit_show_action_buttons(monkeypatch, minimal_css: Path):
    from GONet_Wizard.commands.show import command as show_command

    monkeypatch.setattr("GONet_Wizard.settings.STATIC", minimal_css, raising=False)
    monkeypatch.setattr(
        show_command,
        "build_show_figure",
        lambda *a, **k: _dummy_fig(rows=1, cols=1, per_file_rows=False, height=555),
    )
    monkeypatch.setattr(show_command.pio, "to_html", lambda *a, **k: "<div id='gonet-show-plot'>PLOT</div>")

    args = SimpleNamespace(
        filenames=[Path("x.jpg")],
        blue=True,
        green=False,
        red=False,
        window_width_px=1200,
        window_height_px=700,
    )

    html = show_command.cli_handler(args)
    assert 'gw-save-btn' in html
    assert 'gw-exit-btn' in html
    assert 'Save figure' in html
    assert 'Exit' in html
    assert '/show/session/' in html
    assert 'gonet-pick-save-path' in html
    assert 'showSaveFileTypes' in html
    assert 'PDF files (*.pdf)' in html
    assert 'window.prompt' not in html
    assert 'setTimeout' not in html

from GONet_Wizard.commands.show.layout import (
    _axis_name,
    apply_default_zoom_matches,
    build_zoom_payloads,
    grid_shape_smart,
    add_panel_title_pills,
)


def test_grid_shape_smart_basic():
    assert grid_shape_smart(1) == (1, 1)
    r, c = grid_shape_smart(5)
    assert r * c >= 5


def test_build_zoom_payloads_keys_and_modes():
    payloads = build_zoom_payloads(rows=2, cols=3, per_file_rows=True)
    assert set(payloads.keys()) == {"all", "file", "none"}

    all_p = payloads["all"]
    none_p = payloads["none"]
    file_p = payloads["file"]

    # 'all' links everything to x/y
    assert all_p[f"{_axis_name('xaxis', 4)}.matches"] == "x"
    assert all_p[f"{_axis_name('yaxis', 4)}.matches"] == "y"

    # 'none' breaks all links
    assert none_p[f"{_axis_name('xaxis', 4)}.matches"] is None
    assert none_p[f"{_axis_name('yaxis', 4)}.matches"] is None

    # 'file' links within each row; ensure xaxis4 (row 2 col 1) links to x4
    assert file_p[f"{_axis_name('xaxis', 4)}.matches"] == "x4"
    assert file_p[f"{_axis_name('yaxis', 4)}.matches"] == "y4"


def test_apply_default_zoom_matches_sets_layout_fields():
    fig = go.Figure()
    # Pre-create the axes by setting them on layout (Plotly creates these lazily otherwise)
    for i in range(1, 5):
        fig.layout[_axis_name("xaxis", i)] = {}
        fig.layout[_axis_name("yaxis", i)] = {}

    apply_default_zoom_matches(fig, rows=2, cols=2, mode="none", per_file_rows=False)
    assert fig.layout["xaxis3"]["matches"] is None
    assert fig.layout["yaxis3"]["matches"] is None

    apply_default_zoom_matches(fig, rows=2, cols=2, mode="all", per_file_rows=False)
    assert fig.layout["xaxis3"]["matches"] == "x"
    assert fig.layout["yaxis3"]["matches"] == "y"


def test_add_panel_title_pills_creates_annotations():
    fig = go.Figure()
    # Make it look like a 2x2 subplot layout in terms of domains
    fig.update_layout(width=800, height=600, margin=dict(l=20, r=20, t=20, b=20))
    fig.layout["xaxis"] = dict(domain=[0.0, 0.5])
    fig.layout["yaxis"] = dict(domain=[0.5, 1.0])
    fig.layout["xaxis2"] = dict(domain=[0.5, 1.0])
    fig.layout["yaxis2"] = dict(domain=[0.5, 1.0])
    fig.layout["xaxis3"] = dict(domain=[0.0, 0.5])
    fig.layout["yaxis3"] = dict(domain=[0.0, 0.5])
    fig.layout["xaxis4"] = dict(domain=[0.5, 1.0])
    fig.layout["yaxis4"] = dict(domain=[0.0, 0.5])

    add_panel_title_pills(fig, rows=2, cols=2, titles=["a", "b", "c", "d"])
    assert len(fig.layout.annotations or []) == 4
    assert fig.layout.annotations[0].text == "a"


from GONet_Wizard.commands.show.figure import build_show_figure


class DummyGONet:
    def __init__(self, *, meta: dict, arr: np.ndarray):
        self.meta = meta
        self._arr = arr

    def get_channel(self, ch: str):
        return self._arr


@pytest.fixture
def dummy_arr():
    return np.arange(100, dtype=np.float32).reshape(10, 10)


def test_build_show_figure_single_channel_adds_panel_titles(monkeypatch, dummy_arr):
    """
    In the single-channel path, build_show_figure should call add_panel_title_pills().
    """
    import GONet_Wizard.commands.show.layout as show_layout
    import GONet_Wizard.commands.show.figure as show_figure_mod

    # Patch GONetFile.from_file
    def fake_from_file(_path: str):
        return DummyGONet(meta={"hostname": "cam", "DateTime": "t"}, arr=dummy_arr)

    monkeypatch.setattr(show_figure_mod.GONetFileRaw, "from_file", staticmethod(fake_from_file))

    # Spy on add_panel_title_pills
    calls = {"n": 0}

    def spy_add_panel_title_pills(fig, *, rows, cols, titles, **kwargs):
        calls["n"] += 1
        assert len(titles) == 3

    monkeypatch.setattr(
        show_figure_mod,
        "add_panel_title_pills",
        spy_add_panel_title_pills,
    )

    fig = build_show_figure(
        [Path("a.jpg"), Path("b.jpg"), Path("c.jpg")],
        channels=["blue"],
        window_width_px=900,
        window_height_px=700,
    )

    assert calls["n"] == 1
    meta = fig.layout.meta["show"]
    assert meta["per_file_rows"] is False
    assert meta["cols"] >= 1
    assert meta["rows"] >= 1
    assert meta["filenames"] == ["a.jpg", "b.jpg", "c.jpg"]
    assert meta["channels"] == ["blue"]
    assert meta["panel_titles"] == ["a.jpg", "b.jpg", "c.jpg"]


def test_build_show_figure_multi_channel_adds_row_frames(monkeypatch, dummy_arr):
    """
    In the multi-channel path, build_show_figure should call add_file_row_frames().
    """
    import GONet_Wizard.commands.show.layout as show_layout
    import GONet_Wizard.commands.show.figure as show_figure_mod

    def fake_from_file(_path: str):
        return DummyGONet(meta={"hostname": "cam", "DateTime": "t"}, arr=dummy_arr)

    monkeypatch.setattr(show_figure_mod.GONetFileRaw, "from_file", staticmethod(fake_from_file))

    calls = {"n": 0}

    def spy_add_file_row_frames(fig, *, rows, cols, row_titles, **kwargs):
        calls["n"] += 1
        assert rows == 2
        assert cols == 3
        assert len(row_titles) == 2

    monkeypatch.setattr(
        show_figure_mod,
        "add_file_row_frames",
        spy_add_file_row_frames,
    )

    fig = build_show_figure(
        [Path("a.jpg"), Path("b.jpg")],
        channels=["blue", "green", "red"],
        window_width_px=900,
        window_height_px=700,
    )

    assert calls["n"] == 1
    meta = fig.layout.meta["show"]
    assert meta["per_file_rows"] is True
    assert meta["rows"] == 2
    assert meta["cols"] == 3
    assert meta["filenames"] == ["a.jpg", "b.jpg"]
    assert meta["channels"] == ["blue", "green1", "red"]
    assert meta["row_titles"] == ["cam — a.jpg — t", "cam — b.jpg — t"]


def test_load_gonet_file_for_show_uses_processed_loader_for_tiff(monkeypatch):
    import GONet_Wizard.commands.show.figure as show_figure_mod

    calls = []

    def fake_gonet_from_file(path: str):
        calls.append(("processed", path))
        return "processed-file"

    def fake_raw_from_file(path: str):
        calls.append(("raw", path))
        return "raw-file"

    monkeypatch.setattr(show_figure_mod.GONetFile, "from_file", staticmethod(fake_gonet_from_file))
    monkeypatch.setattr(show_figure_mod.GONetFileRaw, "from_file", staticmethod(fake_raw_from_file))

    assert show_figure_mod._load_gonet_file_for_show(Path("image.tiff")) == "processed-file"
    assert calls[-1] == ("processed", "image.tiff")

    assert show_figure_mod._load_gonet_file_for_show(Path("image.tif")) == "processed-file"
    assert calls[-1] == ("processed", "image.tif")

    assert show_figure_mod._load_gonet_file_for_show(Path("image.jpg")) == "raw-file"
    assert calls[-1] == ("raw", "image.jpg")


def test_channel_for_loaded_file_falls_back_to_green_for_processed_files():
    import GONet_Wizard.commands.show.figure as show_figure_mod

    class ProcessedLike:
        CHANNELS = ["blue", "green", "red"]

    assert show_figure_mod._channel_for_loaded_file(ProcessedLike(), "green1") == "green"
    assert show_figure_mod._channel_for_loaded_file(ProcessedLike(), "green2") == "green"
    assert show_figure_mod._channel_for_loaded_file(ProcessedLike(), "red") == "red"


from GONet_Wizard.commands.show.io import save_figure_plotly


def _simple_show_export_figure() -> go.Figure:
    fig = go.Figure(go.Heatmap(z=np.arange(9).reshape(3, 3), zmin=0, zmax=8, showscale=False))
    fig.update_layout(width=300, height=250, meta={"show": {"rows": 1, "cols": 1}})
    return fig


def test_show_static_export_title_data_uses_show_metadata():
    import GONet_Wizard.commands.show.io as show_io

    fig = go.Figure([
        go.Heatmap(z=np.ones((2, 2))),
        go.Heatmap(z=np.ones((2, 2))),
        go.Heatmap(z=np.ones((2, 2))),
    ])
    fig.update_layout(
        meta={
            "show": {
                "rows": 1,
                "cols": 3,
                "per_file_rows": True,
                "row_titles": ["cam — file.jpg — 2026"],
                "channels": ["blue", "green1", "red"],
            }
        }
    )

    per_file_rows, row_titles, panel_titles, channel_labels = show_io._static_title_data(fig)
    assert per_file_rows is True
    assert row_titles == ["cam — file.jpg — 2026"]
    assert panel_titles == []
    assert channel_labels == ["Blue", "Green", "Red"]


def test_save_figure_plotly_appends_pdf(tmp_path: Path):
    fig = _simple_show_export_figure()
    out = save_figure_plotly(fig, str(tmp_path / "out"))
    assert out.endswith(".pdf")
    assert Path(out).exists()


def test_save_figure_plotly_avoids_overwrite(tmp_path: Path):
    # Pre-create out.pdf so the function must pick out_1.pdf
    (tmp_path / "out.pdf").write_text("existing", encoding="utf-8")

    fig = _simple_show_export_figure()
    out = save_figure_plotly(fig, str(tmp_path / "out.pdf"))
    assert out.endswith("_1.pdf")
    assert Path(out).exists()


def test_save_figure_plotly_html_export_avoids_static_renderer(tmp_path: Path):
    fig = _simple_show_export_figure()
    out = save_figure_plotly(fig, str(tmp_path / "out.html"))
    assert out.endswith(".html")
    assert "plotly" in Path(out).read_text(encoding="utf-8").lower()


def test_save_figure_plotly_static_failure_raises(monkeypatch, tmp_path: Path):
    import GONet_Wizard.commands.show.io as show_io

    def fail_static_export(_fig, _path):
        raise Exception("cannot write")

    monkeypatch.setattr(show_io, "_save_static_matplotlib", fail_static_export)

    fig = _simple_show_export_figure()
    with pytest.raises(RuntimeError) as e:
        save_figure_plotly(fig, str(tmp_path / "out.pdf"))

    assert "failed to export" in str(e.value).lower()
