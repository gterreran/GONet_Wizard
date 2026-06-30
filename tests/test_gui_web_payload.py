from __future__ import annotations

from GONet_Wizard.commands.smart_parser import SmartArgumentParser
from GONet_Wizard.gui.web import payload_to_argv_with_parser


def _extract_parser() -> SmartArgumentParser:
    parser = SmartArgumentParser(description="test")
    subparsers = parser.add_subparsers(dest="command", parser_class=parser.__class__)
    extract = subparsers.add_parser("extract")
    extract.add_argument("filenames", nargs="+")
    extract.add_argument("--angles")
    extract.add_argument("--inner_radius")
    extract.add_argument("--output_type", choices=["json", "csv"])
    extract.add_argument("--red", action="store_true", default=False)
    return parser


def test_gui_payload_uses_equals_form_for_negative_option_values():
    argv = payload_to_argv_with_parser(
        _extract_parser(),
        {
            "command": "extract",
            "filenames": "image.jpg",
            "angles": "-90,90",
        },
    )

    assert argv == ["extract", "image.jpg", "--angles=-90,90"]


def test_gui_payload_uses_registered_option_string_for_underscore_flags():
    argv = payload_to_argv_with_parser(
        _extract_parser(),
        {
            "command": "extract",
            "filenames": "image.jpg",
            "inner_radius": "10",
            "output_type": "csv",
        },
    )

    assert "--inner_radius=10" in argv
    assert "--output_type=csv" in argv
    assert "--inner-radius=10" not in argv
    assert "--output-type=csv" not in argv


def test_smart_parser_accepts_negative_comma_separated_option_value():
    parser = _extract_parser()

    parsed = parser.parse_args(["extract", "image.jpg", "--angles", "-90,90"])

    assert parsed.angles == "-90,90"
