import pytest, subprocess, sys
from GONet_Wizard import commands
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def disable_plt_show(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda: None)

@pytest.fixture(params=["jpg", "tiff"])
def dolus_path_in_tmp(tmp_path, request):
    """
    Fixture that copies either the JPG or TIFF Dolus test image to a temporary path.
    The test will run once for each format.
    """
    ext = request.param
    filename = f"Dolus_250307_155311_1741362791.{ext}"
    source = Path("tests") / filename
    target = tmp_path / f"Dolus.{ext}"
    target.write_bytes(source.read_bytes())
    return target

def test_show_metadata_accepts_single_string_path(tmp_path, capsys):
    from GONet_Wizard.commands.show_meta import show_metadata

    file = tmp_path / "dummy.jpg"
    file.write_bytes(b"not a real image, but enough to exist")

    # Convert string to list
    show_metadata(str(file))

    captured = capsys.readouterr()
    assert f"📂 File: {file}" in captured.out

def test_show_metadata_handles_missing_file(capsys):
    from GONet_Wizard.commands.show_meta import show_metadata

    non_existent = "/this/file/does/not_exist.jpg"
    show_metadata(non_existent)

    captured = capsys.readouterr()
    assert f"📂 File: {non_existent}" in captured.out
    assert "❌ File does not exist." in captured.out

def test_show_metadata_handles_parsing_error(tmp_path, monkeypatch, capsys):
    from GONet_Wizard.GONet_utils import GONetFile
    from GONet_Wizard.commands.cli_core import filter_by_ext

    file = tmp_path / "bad.jpg"
    file.write_text("invalid JPEG content")

    # Monkeypatch from_file to raise an exception
    monkeypatch.setattr(GONetFile, "from_file", lambda _: (_ for _ in ()).throw(ValueError("simulated failure")))

    files = filter_by_ext([str(file)], [".jpg", ".tiff"])
    commands.show.show_gonet_files(files)

    captured = capsys.readouterr()
    assert f"⚠️ Error reading file {file}: simulated failure" in captured.out

def test_show_meta_prints_expected_output(capsys, dolus_path_in_tmp):
    from GONet_Wizard import commands

    commands.show_meta.show_metadata([str(dolus_path_in_tmp)])

    captured = capsys.readouterr()
    output = captured.out
    assert f"📂 File: {dolus_path_in_tmp}" in output
    assert "🧾 Metadata:" in output or "ℹ️ No metadata" in output


def test_cli_show_meta(dolus_path_in_tmp):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "GONet_Wizard", "show_meta", str(dolus_path_in_tmp)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert f"📂 File: {dolus_path_in_tmp}" in result.stdout
    assert "🧾 Metadata:" in result.stdout or "ℹ️ No metadata" in result.stdout


def test_show_all_channels_runs(dolus_path_in_tmp):
    """
    Test that show() runs successfully with all channels enabled implicitly.
    """
    commands.show.show_gonet_files([str(dolus_path_in_tmp)])  # should show all channels (auto)
    # No error = pass

def test_show_empty_list():
    with pytest.raises(ValueError):
        commands.show.show_gonet_files([])

def test_show_uneven_number_of_plots(dolus_path_in_tmp):
    """
    Test that show() runs successfully with all channels enabled implicitly.
    """
    commands.show.show_gonet_files([str(dolus_path_in_tmp)]*5, red=True)

@pytest.mark.parametrize("channels", [
    {"red": True},
    {"green": True},
    {"blue": True},
    {"red": True, "blue": True},
    {"green": True, "blue": True}
])
def test_show_selected_channels(dolus_path_in_tmp, channels):
    """
    Test that show() works with selected channel combinations.
    """
    commands.show.show_gonet_files([str(dolus_path_in_tmp)], **channels)
    # No error = pass

@pytest.mark.parametrize("output", ['output.pdf', 'output'])
def test_show_saves_figure(dolus_path_in_tmp, tmp_path, output):
    """
    Test that show() saves a figure when requested.
    """
    save_path = tmp_path / output
    commands.show.show_gonet_files([str(dolus_path_in_tmp)], save=str(save_path), red=True)

    if not output.endswith(".pdf"):
        assert save_path.with_suffix(".pdf").exists()
    else:
        assert save_path.exists() or save_path.with_name("output_1.pdf").exists(), "Expected saved PDF not found."


def test_show_overwrite_handling(dolus_path_in_tmp, tmp_path):
    """
    Test that repeated calls to save create non-conflicting filenames.
    """
    save_path = tmp_path / "plot.pdf"

    # Save twice with the same name
    commands.show.show_gonet_files([str(dolus_path_in_tmp)], save=str(save_path), red=True)
    commands.show.show_gonet_files([str(dolus_path_in_tmp)], save=str(save_path), red=True)

    first = save_path
    second = tmp_path / "plot_1.pdf"

    assert first.exists(), "First saved figure not found."
    assert second.exists(), "Second figure with suffix not saved correctly."


def test_cli_show_basic(tmp_path):
    """
    CLI test: Run the `show` command on a .jpg file and confirm no GUI window opens.
    """
    source = Path("tests/Dolus_250307_155311_1741362791.jpg")
    test_file = tmp_path / "Dolus.jpg"
    test_file.write_bytes(source.read_bytes())

    output_pdf = tmp_path / "output.pdf"

    result = subprocess.run(
        [
            sys.executable, "tests/_plt_patch.py", "show",
            str(test_file), "--red", "--save", str(output_pdf)
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_pdf.exists(), "Expected output PDF was not created"

