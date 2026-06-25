from __future__ import annotations

import argparse
from typing import Any

import pytest


@pytest.fixture
def fake_cli_tree(monkeypatch):
    """
    Patch cli_core.build_subparser to install a minimal command tree.

    The real project command tree can import many modules; for unit tests we keep
    parsing deterministic and avoid side effects.
    """

    def _build_subparser(parser: argparse.ArgumentParser, package: Any) -> argparse.ArgumentParser:
        # Important: use parser_class=parser.__class__ to mimic real behavior
        # (this ensures SmartArgumentParser is used for subparsers too).
        subparsers = parser.add_subparsers(dest="command", help="commands", parser_class=parser.__class__)

        # show: requires at least one filename positional
        show_p = subparsers.add_parser("show", help="show help")
        show_p.add_argument("filenames", nargs="+", help="input files")

        # a dummy handler so "show file" would parse successfully if we wanted to test it
        def _handler(args: argparse.Namespace) -> None:
            return None

        show_p.set_defaults(handler=_handler)

        # other: no args, used to ensure a non-error parse path exists if needed
        other_p = subparsers.add_parser("other", help="other help")
        other_p.set_defaults(handler=_handler)

        return parser

    # Patch where cli.py imports it (GONet_Wizard.cli.cli_core.build_subparser)
    monkeypatch.setattr("GONet_Wizard.cli.cli_core.build_subparser", _build_subparser, raising=True)


@pytest.fixture
def open_form_spy(monkeypatch):
    """
    Spy on open_command_form without triggering any UI side effects.
    """
    calls: list[dict[str, object]] = []

    def _fake_open_command_form(*, cmd_tokens, port: int, debug_webview: bool) -> None:
        calls.append(
            {
                "cmd_tokens": tuple(cmd_tokens),
                "port": port,
                "debug_webview": debug_webview,
            }
        )

    monkeypatch.setattr("GONet_Wizard.ui.launch_forms.open_command_form", _fake_open_command_form, raising=True)
    return calls


def test_cli_redirects_to_form_on_command_only_missing_required(fake_cli_tree, open_form_spy, capsys):
    """
    `GONet_Wizard show` (command only, missing required filenames) should open the show form.
    """
    from GONet_Wizard import cli

    cli.main(["show"])

    assert len(open_form_spy) == 1
    assert open_form_spy[0]["cmd_tokens"] == ("show",)
    assert open_form_spy[0]["port"] == 5050
    assert open_form_spy[0]["debug_webview"] is False

    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""


def test_cli_does_not_redirect_on_unknown_option(fake_cli_tree, open_form_spy, capsys):
    """
    `GONet_Wizard show --nope` is an argparse error, but not a command-only invocation.
    It should NOT open the form; it should print usage/error to stderr.
    """
    from GONet_Wizard import cli

    cli.main(["show", "--nope"])

    assert open_form_spy == []

    out = capsys.readouterr()
    assert "usage:" in out.out.lower()
    assert "error:" in out.err.lower()


def test_cli_does_not_redirect_on_unknown_command(fake_cli_tree, open_form_spy, capsys):
    """
    `GONet_Wizard shwo` should not open a form (unknown command).
    """
    from GONet_Wizard import cli

    cli.main(["shwo"])

    assert open_form_spy == []

    out = capsys.readouterr()
    assert "usage:" in out.out.lower()
    # argparse wording varies slightly by version; this is the common substring
    assert "invalid choice" in out.err.lower()


def test_cli_redirect_uses_preparsed_ui_flags(fake_cli_tree, open_form_spy, capsys):
    """
    Global flags are pre-parsed even when full parsing fails, and are forwarded
    to open_command_form.
    """
    from GONet_Wizard import cli

    cli.main(["--ui-port", "6001", "--debug-webview", "show"])

    assert len(open_form_spy) == 1
    assert open_form_spy[0]["cmd_tokens"] == ("show",)
    assert open_form_spy[0]["port"] == 6001
    assert open_form_spy[0]["debug_webview"] is True

    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""


def test_cli_successful_parse_calls_handler(fake_cli_tree, open_form_spy, capsys, monkeypatch):
    from GONet_Wizard import cli

    called = {"n": 0}

    def _build_subparser(parser, package):
        sp = parser.add_subparsers(dest="command", parser_class=parser.__class__)
        p = sp.add_parser("show")
        p.add_argument("filenames", nargs="+")
        def _handler(args):
            called["n"] += 1
        p.set_defaults(handler=_handler)
        return parser

    monkeypatch.setattr("GONet_Wizard.cli.cli_core.build_subparser", _build_subparser, raising=True)

    cli.main(["show", "a.fits"])

    assert called["n"] == 1
    assert open_form_spy == []
    out = capsys.readouterr()
    assert out.err == ""
