from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import main

from tests.helpers import parse_cell_blocks, write_notebook


def test_end_to_end_flow_and_reload_behavior(tmp_path: Path) -> None:
    notebook_path = tmp_path / "flow.ipynb"
    write_notebook(notebook_path)

    loaded = cast(dict[str, Any], main.load_notebook(str(notebook_path)))
    assert set(loaded) == {"path", "total_cells", "active_cells"}
    assert loaded["total_cells"] == 3
    assert loaded["active_cells"] == 3

    notebook_text = cast(str, main.read_notebook())
    assert "[index:0 type:markdown]" in notebook_text
    assert "one two three four five six seven eight nine ten eleven" in notebook_text
    assert "[index:1 type:code]" in notebook_text
    assert "print('hello world')\nvalue = 10" in notebook_text
    assert "[index:2 type:raw]" in notebook_text
    assert "raw payload" in notebook_text

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
    added_blocks = parse_cell_blocks(added_text)
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
    removed_blocks = parse_cell_blocks(removed_text)
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
