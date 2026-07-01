from __future__ import annotations

from pathlib import Path

from flask import Flask

from GONet_Wizard.gui import web


def _template_app() -> Flask:
    template_dir = Path(web.__file__).with_name("templates")
    app = Flask(__name__, template_folder=str(template_dir))
    app.register_blueprint(web.launcher_bp)
    return app


def test_extract_page_uses_terminal_without_duplicate_feedback_div():
    app = _template_app()

    with app.test_client() as client:
        response = client.get("/cmd/extract")

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="command-terminal"' in html
    assert 'id="terminal-output"' in html
    assert 'id="output"' not in html


def test_show_page_uses_terminal_without_regular_feedback_div():
    app = _template_app()

    with app.test_client() as client:
        response = client.get("/cmd/show")

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="command-terminal"' in html
    assert 'id="terminal-output"' in html
    assert 'id="output"' not in html
    assert 'name="save"' not in html
    assert 'show-save' not in html


def test_show_meta_page_uses_terminal_without_regular_feedback_div():
    app = _template_app()

    with app.test_client() as client:
        response = client.get("/cmd/show_meta")

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="command-terminal"' in html
    assert 'id="terminal-output"' in html
    assert 'id="output"' not in html
    assert 'name="html"' in html
    assert 'name="save"' not in html


def test_extract_page_lists_interactive_shape_once():
    app = _template_app()

    with app.test_client() as client:
        response = client.get("/cmd/extract")

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert html.count('value="interactive"') == 1
    assert 'value="">Interactive</option>' not in html
