from pathlib import Path

import pytest

from scripts.extract_inline_script import InlineScriptError, extract_literal_string


def test_extracts_named_literal_without_importing_module(tmp_path: Path) -> None:
    webapp = tmp_path / "webapp.py"
    webapp.write_text(
        'raise RuntimeError("must not import")\nSCRIPT = "const answer = 42;\\n"\n',
        encoding="utf-8",
    )

    assert extract_literal_string(webapp, "SCRIPT") == "const answer = 42;\n"


def test_rejects_non_literal_script_assignment(tmp_path: Path) -> None:
    webapp = tmp_path / "webapp.py"
    webapp.write_text('SCRIPT = get_script()\n', encoding="utf-8")

    with pytest.raises(InlineScriptError, match="plain string literal"):
        extract_literal_string(webapp, "SCRIPT")


def test_rejects_missing_script_assignment(tmp_path: Path) -> None:
    webapp = tmp_path / "webapp.py"
    webapp.write_text('STYLE = "body {}"\n', encoding="utf-8")

    with pytest.raises(InlineScriptError, match="not found"):
        extract_literal_string(webapp, "SCRIPT")
