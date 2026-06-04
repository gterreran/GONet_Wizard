import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from GONet_Wizard.commands import inputs
from GONet_Wizard.commands import parser_builder


class RecordingParser(argparse.ArgumentParser):
    pass


def make_command(name="demo", args=None, handler=True):
    command = SimpleNamespace(
        COMMAND=SimpleNamespace(
            name=name,
            help=f"{name} help",
            args=args or [],
        )
    )
    if handler:
        command.cli_handler = lambda parsed: parsed
    return command


def test_register_simple_subcommand_adds_positional_flags_and_handler(monkeypatch):
    wrapped_handlers = []

    def fake_wrap(cmd):
        wrapped_handlers.append(cmd)
        return f"wrapped:{cmd.COMMAND.name}"

    monkeypatch.setattr(parser_builder, "wrap_handler_for_ui", fake_wrap)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    command = make_command(
        args=[
            {"dest": "filename"},
            {"flags": ["--count"], "type": int, "default": 1},
        ]
    )

    parser_builder.register_simple_subcommand(subparsers, command)
    parsed = parser.parse_args(["demo", "image.tiff", "--count", "3"])

    assert parsed.command == "demo"
    assert parsed.filename == "image.tiff"
    assert parsed.count == 3
    assert parsed.handler == "wrapped:demo"
    assert wrapped_handlers == [command]


def test_register_simple_subcommand_without_handler_only_registers_arguments():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    command = make_command(handler=False)

    parser_builder.register_simple_subcommand(subparsers, command)
    parsed = parser.parse_args(["demo"])

    assert parsed.command == "demo"
    assert not hasattr(parsed, "handler")


def test_build_subparser_uses_parent_parser_class_and_nested_packages(monkeypatch):
    monkeypatch.setattr(
        parser_builder,
        "wrap_handler_for_ui",
        lambda cmd: f"handler:{cmd.COMMAND.name}",
    )

    group_command = make_command(name="group", handler=False)
    leaf_command = make_command(name="leaf", args=[{"flags": ["--value"], "default": "x"}])

    child_package = SimpleNamespace(
        PARSER=SimpleNamespace(
            dest="leaf_command",
            help="leaf commands",
            args={"commands": [leaf_command]},
        )
    )
    root_package = SimpleNamespace(
        PARSER=SimpleNamespace(
            dest="root_command",
            help="root commands",
            args={
                "commands": [group_command],
                "subparsers": [
                    {"parser_name": "group", "package": child_package},
                ],
            },
        )
    )

    parser = RecordingParser()
    returned = parser_builder.build_subparser(parser, root_package)
    parsed = parser.parse_args(["group", "leaf", "--value", "42"])

    assert returned is parser
    assert parsed.root_command == "group"
    assert parsed.leaf_command == "leaf"
    assert parsed.value == "42"
    assert parsed.handler == "handler:leaf"


def test_expand_inputs_handles_comma_lists_directories_globs_and_dedupes(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    c = tmp_path / "c.dat"
    nested = tmp_path / "nested"
    nested.mkdir()
    d = nested / "d.txt"
    ignored_dir = nested / "subdir"
    ignored_dir.mkdir()

    for path in [a, b, c, d]:
        path.write_text(path.name)

    expanded = inputs.expand_inputs(
        [
            f"{a},{b}",
            str(nested),
            str(tmp_path / "*.dat"),
            str(a),
        ]
    )

    assert expanded == [a, b, d, c]


def test_expand_inputs_ignores_empty_comma_parts(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("a")

    assert inputs.expand_inputs([f" , {a}, "]) == [a]


def test_expand_inputs_raises_for_unmatched_token(tmp_path):
    with pytest.raises(FileNotFoundError, match="No files matched"):
        inputs.expand_inputs([str(tmp_path / "missing*.txt")])


def test_expand_filenames_action_converts_unmatched_files_to_parser_error(tmp_path):
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", action=inputs.ExpandFilenames)

    with pytest.raises(SystemExit):
        parser.parse_args([str(tmp_path / "missing.txt")])


def test_expand_filenames_action_sets_expanded_paths(tmp_path):
    path = tmp_path / "image.tiff"
    path.write_text("fake")
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", action=inputs.ExpandFilenames)

    parsed = parser.parse_args([str(path)])

    assert parsed.files == [path]


def test_filter_by_ext_normalizes_case_and_missing_dots():
    paths = [Path("a.JSON"), Path("b.txt"), Path("c.TIFF")]

    assert inputs.filter_by_ext(paths, ["json", ".tiff"]) == [paths[0], paths[2]]


def test_filter_by_ext_raises_when_no_paths_match():
    with pytest.raises(inputs.ExtensionFilterError, match="No files matched"):
        inputs.filter_by_ext([Path("a.txt")], ["json"])
