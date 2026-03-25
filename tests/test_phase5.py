from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any, Generator, cast
from unittest.mock import patch

from fastmcp.exceptions import ToolError
import nbformat
from nbformat.notebooknode import NotebookNode
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


CELL_HEADER_RE = re.compile(r"^\[index:(\d+) type:(code|markdown|raw)\]$")


def _reset_session() -> None:
    main.session.path = None
    main.session.nb = None
    main.session.dirty = False


def _write_notebook(path: Path, cells: list[NotebookNode] | None = None) -> None:
    notebook = nbformat.v4.new_notebook(
        cells=cells
        if cells is not None
        else [
            nbformat.v4.new_markdown_cell(
                "one two three four five six seven eight nine ten eleven"
            ),
            nbformat.v4.new_code_cell("print('hello world')\nvalue = 10"),
            nbformat.v4.new_raw_cell("raw payload"),
        ]
    )
    nbformat.write(notebook, path)


def _parse_cell_blocks(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    header_positions = [
        line_index
        for line_index, line in enumerate(lines)
        if CELL_HEADER_RE.match(line)
    ]
    assert header_positions

    blocks: list[dict[str, object]] = []
    for i, block_start in enumerate(header_positions):
        match = CELL_HEADER_RE.match(lines[block_start])
        assert match is not None

        block_end = (
            header_positions[i + 1] if i + 1 < len(header_positions) else len(lines)
        )
        source_end = block_end
        if (
            i + 1 < len(header_positions)
            and source_end > block_start
            and lines[source_end - 1] == ""
        ):
            source_end -= 1

        source_start = block_start + 1
        if source_start < source_end and lines[source_start] == "":
            source_start += 1

        source = "\n".join(lines[source_start:source_end])
        blocks.append(
            {
                "index": int(match.group(1)),
                "type": match.group(2),
                "source": source,
            }
        )

    return blocks


@pytest.fixture(autouse=True)
def reset_session_fixture() -> Generator[None, None, None]:
    _reset_session()
    yield
    _reset_session()


def test_end_to_end_flow_and_reload_behavior(tmp_path: Path) -> None:
    notebook_path = tmp_path / "flow.ipynb"
    _write_notebook(notebook_path)

    loaded = cast(dict[str, Any], main.load_notebook(str(notebook_path)))
    assert set(loaded) == {"path", "total_cells", "active_cells"}
    assert loaded["total_cells"] == 3
    assert loaded["active_cells"] == 3

    outline = cast(str, main.read_outline())
    assert "[index:0 type:markdown]" in outline
    assert "one two three four five six seven eight nine ten eleven" in outline
    assert "[index:1 type:code]" in outline
    assert "print('hello world')\nvalue = 10" in outline
    assert "[index:2 type:raw]" in outline
    assert "raw payload" in outline

    search = cast(dict[str, Any], main.search_cell("hello"))
    assert set(search) == {"keywords", "results"}
    assert search["keywords"] == ["hello"]
    assert search["results"][0]["index"] == 1
    assert search["results"][0]["snippets"]

    replaced = cast(dict[str, Any], main.replace_cell(1, "print('hello edited')"))
    assert set(replaced) == {"index", "updated", "chars"}
    assert replaced["index"] == 1
    assert replaced["updated"] is True

    added_text = cast(
        str,
        main.add_cell("extra details", cell_type="markdown", index=1),
    )
    added_blocks = _parse_cell_blocks(added_text)
    assert len(added_blocks) == 3
    assert added_blocks[0] == {
        "index": 2,
        "type": "markdown",
        "source": "extra details",
    }
    assert added_blocks[1]["index"] == 1
    assert added_blocks[1]["type"] == "code"
    assert added_blocks[2]["index"] == 3
    assert added_blocks[2]["type"] == "raw"

    removed_text = cast(str, main.remove_cell(0))
    removed_blocks = _parse_cell_blocks(removed_text)
    assert len(removed_blocks) == 2
    assert removed_blocks[0]["index"] == 0
    assert removed_blocks[0]["type"] == "markdown"
    assert removed_blocks[1]["index"] == 1
    assert removed_blocks[1]["type"] == "code"

    first_cell = cast(dict[str, Any], main.read_cell(0))
    assert first_cell["type"] == "code"
    assert "hello edited" in str(first_cell["source"])

    saved_copy_path = tmp_path / "flow_copy.ipynb"
    save_result = cast(dict[str, Any], main.save_notebook(str(saved_copy_path)))
    assert set(save_result) == {"path", "saved", "active_cells"}
    assert save_result["path"] == str(saved_copy_path)
    assert save_result["active_cells"] == 3

    reloaded = cast(dict[str, Any], main.load_notebook(str(saved_copy_path)))
    assert reloaded["total_cells"] == 3


def test_standardized_errors_for_contract_failures(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as err:
        main.read_cell(0)
    assert str(err.value) == "No notebook is loaded. Use load_notebook(path) first."

    notebook_path = tmp_path / "errors.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    with pytest.raises(ToolError) as err:
        main.read_cell(-1)
    assert str(err.value) == "Cell index -1 is out of range."

    main.remove_cell(2)
    with pytest.raises(ToolError) as err:
        main.remove_cell(2)
    assert str(err.value) == "Cell index 2 is out of range."

    invalid_path = tmp_path / "invalid.ipynb"
    invalid_path.write_text('{"nbformat": 4, "cells": "bad"}', encoding="utf-8")
    with pytest.raises(ToolError) as err:
        main.load_notebook(str(invalid_path))
    assert "Invalid notebook file" in str(err.value)


def test_autosave_failure_is_actionable(tmp_path: Path) -> None:
    first_path = tmp_path / "first.ipynb"
    second_path = tmp_path / "second.ipynb"
    _write_notebook(first_path)
    _write_notebook(second_path)
    main.load_notebook(str(first_path))

    with patch("main.nbformat.write", side_effect=RuntimeError("disk full")):
        with pytest.raises(ToolError) as err:
            main.load_notebook(str(second_path))

    assert "Autosave failed" in str(err.value)
    assert "disk full" in str(err.value)


def test_load_notebook_file_not_found_has_actionable_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.ipynb"

    with pytest.raises(ToolError) as err:
        main.load_notebook(str(missing_path))

    message = str(err.value)
    assert "Notebook file not found" in message
    assert str(missing_path) in message


def test_save_notebook_without_loaded_notebook_fails() -> None:
    with pytest.raises(ToolError) as err:
        main.save_notebook()
    assert str(err.value) == "No notebook is loaded. Use load_notebook(path) first."


def test_add_cell_normalizes_valid_cell_types_and_rejects_invalid(
    tmp_path: Path,
) -> None:
    notebook_path = tmp_path / "types.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    added_markdown = cast(
        str,
        main.add_cell("extra", cell_type=" Markdown "),
    )
    assert _parse_cell_blocks(added_markdown)[0]["type"] == "markdown"

    added_raw = cast(str, main.add_cell("raw extra", cell_type="RAW"))
    assert _parse_cell_blocks(added_raw)[0]["type"] == "raw"

    with pytest.raises(ToolError) as err:
        main.add_cell("oops", cell_type="sql")

    assert (
        str(err.value)
        == "Unsupported cell type 'sql'. Use one of: code, markdown, raw."
    )


def test_add_cell_supports_insert_below_index(tmp_path: Path) -> None:
    notebook_path = tmp_path / "insert.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    inserted_text = cast(str, main.add_cell("inserted", cell_type="code", index=0))
    inserted_blocks = _parse_cell_blocks(inserted_text)
    assert inserted_blocks[0]["index"] == 1
    assert inserted_blocks[0]["source"] == "inserted"

    cell = cast(dict[str, Any], main.read_cell(1))
    assert cell["source"] == "inserted"


def test_search_cell_with_empty_keywords_returns_empty_results(tmp_path: Path) -> None:
    notebook_path = tmp_path / "search-empty.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    assert main.search_cell("   ") == {"keywords": [], "results": []}


def test_search_cell_requires_all_keywords_and_respects_real_removal(
    tmp_path: Path,
) -> None:
    notebook_path = tmp_path / "search-all.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    found = cast(dict[str, Any], main.search_cell("hello value"))
    assert found["keywords"] == ["hello", "value"]
    assert [result["index"] for result in found["results"]] == [1]

    main.remove_cell(1)
    assert main.search_cell("hello value")["results"] == []


def test_markdown_preview_handles_short_and_long_content() -> None:
    short_preview = main._format_markdown_preview("one   two", char_limit=20)
    long_preview = main._format_markdown_preview(
        "one two three four five six seven eight nine ten eleven",
        char_limit=20,
    )

    assert short_preview == "one two"
    assert long_preview.endswith(" ...")
    assert long_preview.startswith("one two three four")
    assert len(long_preview) <= 24


def test_extract_search_snippets_handles_overlap_and_empty_inputs() -> None:
    source = "alpha beta gamma delta epsilon"

    snippets = main._extract_search_snippets(source, ["beta", "gamma"], context_words=1)
    assert snippets == ["... alpha beta gamma delta ..."]
    assert main._extract_search_snippets("", ["alpha"]) == []
    assert main._extract_search_snippets(source, []) == []
    assert main._extract_search_snippets(source, [""]) == []


def test_new_cell_factory_creates_supported_types() -> None:
    assert main._new_cell("code", "print('x')").cell_type == "code"
    assert main._new_cell("markdown", "# title").cell_type == "markdown"
    assert main._new_cell("raw", "payload").cell_type == "raw"


def test_save_notebook_validation_failure_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "validation.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    with patch("main.nbformat.validate", side_effect=ValueError("bad schema")):
        with pytest.raises(ToolError) as err:
            main.save_notebook()

    assert str(err.value) == "Save failed: notebook is invalid: bad schema"


def test_load_notebook_autosaves_dirty_changes_before_switching(tmp_path: Path) -> None:
    first_path = tmp_path / "autosave-first.ipynb"
    second_path = tmp_path / "autosave-second.ipynb"
    _write_notebook(first_path)
    _write_notebook(second_path)

    main.load_notebook(str(first_path))
    main.replace_cell(1, "print('autosaved update')")
    main.remove_cell(2)

    loaded = cast(dict[str, Any], main.load_notebook(str(second_path)))
    assert loaded["path"] == str(second_path)
    assert main.session.path == str(second_path)
    assert main.session.dirty is False

    autosaved_first = nbformat.read(first_path, as_version=4)
    assert len(autosaved_first.cells) == 2
    assert "autosaved update" in str(autosaved_first.cells[1].source)


def test_delete_cell_is_alias_of_remove_cell(tmp_path: Path) -> None:
    notebook_path = tmp_path / "alias.ipynb"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    removed = cast(str, main.delete_cell(0))
    blocks = _parse_cell_blocks(removed)
    assert blocks[0]["index"] == 0
    assert blocks[0]["type"] == "markdown"


def test_to_markdown_outputs_full_cell_contents(tmp_path: Path) -> None:
    notebook_path = tmp_path / "full-md.ipynb"
    _write_notebook(
        notebook_path,
        cells=[
            nbformat.v4.new_markdown_cell("# Title\n\n- item 1\n- item 2\n"),
            nbformat.v4.new_code_cell("print('line1')\nprint('line2')"),
        ],
    )
    main.load_notebook(str(notebook_path))

    exported = cast(str, main.to_markdown())
    assert "[index:0 type:markdown]" in exported
    assert "# Title\n\n- item 1\n- item 2\n" in exported
    assert "[index:1 type:code]" in exported
    assert "print('line1')\nprint('line2')" in exported


def test_from_markdown_replaces_current_notebook_cells(tmp_path: Path) -> None:
    notebook_path = tmp_path / "from-md.ipynb"
    markdown_path = tmp_path / "input.md"
    _write_notebook(notebook_path)

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


def test_from_markdown_supports_round_trip_with_to_markdown(tmp_path: Path) -> None:
    notebook_path = tmp_path / "roundtrip.ipynb"
    markdown_path = tmp_path / "roundtrip.md"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    exported = cast(str, main.to_markdown())
    markdown_path.write_text(exported, encoding="utf-8")

    main.replace_cell(0, "changed")
    main.from_markdown(str(markdown_path))

    restored = cast(str, main.to_markdown())
    assert restored == exported


def test_from_markdown_invalid_format_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "invalid-md.ipynb"
    markdown_path = tmp_path / "invalid.md"
    _write_notebook(notebook_path)
    markdown_path.write_text("not a valid exported notebook", encoding="utf-8")
    main.load_notebook(str(notebook_path))

    with pytest.raises(ToolError) as err:
        main.from_markdown(str(markdown_path))

    assert "no cell headers found" in str(err.value)


def test_from_markdown_file_not_found_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "missing-md.ipynb"
    missing_path = tmp_path / "missing.md"
    _write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    with pytest.raises(ToolError) as err:
        main.from_markdown(str(missing_path))

    assert "Markdown file not found" in str(err.value)
