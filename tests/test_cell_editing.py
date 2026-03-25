from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastmcp.exceptions import ToolError
import pytest

import main
from jupyter_notebook_mcp.notebook_io import _new_cell

from tests.helpers import parse_cell_blocks, write_notebook


def test_add_cell_normalizes_valid_cell_types_and_rejects_invalid(
    tmp_path: Path,
) -> None:
    notebook_path = tmp_path / "types.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    added_markdown = cast(
        str,
        main.add_cell("extra", cell_type=" Markdown "),
    )
    assert parse_cell_blocks(added_markdown)[0]["type"] == "markdown"

    added_raw = cast(str, main.add_cell("raw extra", cell_type="RAW"))
    assert parse_cell_blocks(added_raw)[0]["type"] == "raw"

    with pytest.raises(ToolError) as err:
        main.add_cell("oops", cell_type="sql")

    assert (
        str(err.value)
        == "Unsupported cell type 'sql'. Use one of: code, markdown, raw."
    )


def test_add_cell_supports_insert_below_index(tmp_path: Path) -> None:
    notebook_path = tmp_path / "insert.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    inserted_text = cast(str, main.add_cell("inserted", cell_type="code", index=0))
    inserted_blocks = parse_cell_blocks(inserted_text)
    assert inserted_blocks[0]["index"] == 1
    assert inserted_blocks[0]["source"] == "inserted"

    cell = cast(dict[str, Any], main.read_cell(1))
    assert cell["source"] == "inserted"


def test_new_cell_factory_creates_supported_types() -> None:
    assert _new_cell("code", "print('x')").cell_type == "code"
    assert _new_cell("markdown", "# title").cell_type == "markdown"
    assert _new_cell("raw", "payload").cell_type == "raw"


def test_delete_cell_is_alias_of_remove_cell(tmp_path: Path) -> None:
    notebook_path = tmp_path / "alias.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    removed = cast(str, main.delete_cell(0))
    blocks = parse_cell_blocks(removed)
    assert blocks[0]["index"] == 0
    assert blocks[0]["type"] == "markdown"
