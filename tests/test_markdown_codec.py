from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastmcp.exceptions import ToolError
import nbformat
import pytest

import main

from tests.helpers import write_notebook


def test_read_notebook_outputs_full_cell_contents(tmp_path: Path) -> None:
    notebook_path = tmp_path / "full-md.ipynb"
    write_notebook(
        notebook_path,
        cells=[
            nbformat.v4.new_markdown_cell("# Title\n\n- item 1\n- item 2\n"),
            nbformat.v4.new_code_cell("print('line1')\nprint('line2')"),
        ],
    )
    main.load_notebook(str(notebook_path))

    exported = cast(str, main.read_notebook())
    assert "[index:0 type:markdown]" in exported
    assert "# Title\n\n- item 1\n- item 2\n" in exported
    assert "[index:1 type:code]" in exported
    assert "print('line1')\nprint('line2')" in exported


def test_from_markdown_replaces_current_notebook_cells(tmp_path: Path) -> None:
    notebook_path = tmp_path / "from-md.ipynb"
    markdown_path = tmp_path / "input.md"
    write_notebook(notebook_path)

    markdown_path.write_text(
        "[index:0 type:markdown]\n\n# Imported\n\n[index:1 type:code]\n\nprint('new')\n",
        encoding="utf-8",
    )

    main.load_notebook(str(notebook_path))
    result = cast(dict[str, Any], main.from_markdown(str(markdown_path)))

    assert result == {"path": str(markdown_path), "replaced": True, "cells": 2}
    assert main.session.dirty is True

    first = cast(dict[str, Any], main.read_cell(0))
    second = cast(dict[str, Any], main.read_cell(1))
    assert first["type"] == "markdown"
    assert first["source"] == "# Imported"
    assert second["type"] == "code"
    assert second["source"] == "print('new')"


def test_from_markdown_supports_round_trip_with_read_notebook(tmp_path: Path) -> None:
    notebook_path = tmp_path / "roundtrip.ipynb"
    markdown_path = tmp_path / "roundtrip.md"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    exported = cast(str, main.read_notebook())
    markdown_path.write_text(exported, encoding="utf-8")

    main.replace_cell(0, "changed")
    main.from_markdown(str(markdown_path))

    restored = cast(str, main.read_notebook())
    assert restored == exported


def test_save_markdown_writes_same_content_as_read_notebook(tmp_path: Path) -> None:
    notebook_path = tmp_path / "save-md.ipynb"
    markdown_path = tmp_path / "save-md.md"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    expected = cast(str, main.read_notebook())
    result = cast(dict[str, Any], main.save_markdown(str(markdown_path)))

    assert result == {"path": str(markdown_path), "saved": True, "cells": 3}
    assert markdown_path.read_text(encoding="utf-8") == expected


def test_from_markdown_invalid_format_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "invalid-md.ipynb"
    markdown_path = tmp_path / "invalid.md"
    write_notebook(notebook_path)
    markdown_path.write_text("not a valid exported notebook", encoding="utf-8")
    main.load_notebook(str(notebook_path))

    with pytest.raises(ToolError) as err:
        main.from_markdown(str(markdown_path))

    assert "no cell headers found" in str(err.value)


def test_from_markdown_file_not_found_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "missing-md.ipynb"
    missing_path = tmp_path / "missing.md"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    with pytest.raises(ToolError) as err:
        main.from_markdown(str(missing_path))

    assert "Markdown file not found" in str(err.value)


def test_save_markdown_write_failure_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "save-md-fail.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    invalid_target = tmp_path / "missing-parent" / "output.md"
    with pytest.raises(ToolError) as err:
        main.save_markdown(str(invalid_target))

    assert "Failed to save markdown file" in str(err.value)
