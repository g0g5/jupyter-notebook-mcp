from __future__ import annotations

from pathlib import Path
import re

import nbformat
from nbformat.notebooknode import NotebookNode


CELL_HEADER_RE = re.compile(r"^\[index:(\d+) type:(code|markdown|raw)\]$")


def write_notebook(path: Path, cells: list[NotebookNode] | None = None) -> None:
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


def parse_cell_blocks(text: str) -> list[dict[str, object]]:
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
