from __future__ import annotations

import re
from pathlib import Path

from fastmcp.exceptions import ToolError
from nbformat.notebooknode import NotebookNode

from .formatting import _render_cell_block
from .notebook_io import _new_cell
from .session import _require_notebook_loaded, session


CELL_HEADER_RE = re.compile(r"^\[index:(\d+) type:(code|markdown|raw)\]$")


def _parse_markdown_document(content: str) -> list[NotebookNode]:
    lines = content.splitlines()
    header_positions = [
        line_index
        for line_index, line in enumerate(lines)
        if CELL_HEADER_RE.match(line)
    ]

    if not header_positions:
        if content.strip() == "":
            return []
        raise ToolError("Invalid markdown notebook format: no cell headers found.")

    if any(line.strip() for line in lines[: header_positions[0]]):
        raise ToolError(
            "Invalid markdown notebook format: unexpected content before first cell header."
        )

    parsed_cells: list[NotebookNode] = []
    for block_idx, block_start in enumerate(header_positions):
        header_match = CELL_HEADER_RE.match(lines[block_start])
        assert header_match is not None

        declared_index = int(header_match.group(1))
        expected_index = block_idx
        if declared_index != expected_index:
            raise ToolError(
                "Invalid markdown notebook format: "
                f"expected index {expected_index}, got {declared_index}."
            )

        block_end = (
            header_positions[block_idx + 1]
            if block_idx + 1 < len(header_positions)
            else len(lines)
        )
        source_end = block_end
        if (
            block_idx + 1 < len(header_positions)
            and source_end > block_start
            and lines[source_end - 1] == ""
        ):
            source_end -= 1

        source_start = block_start + 1
        if source_start < source_end and lines[source_start] == "":
            source_start += 1

        source = "\n".join(lines[source_start:source_end])
        parsed_cells.append(_new_cell(header_match.group(2), source))

    return parsed_cells


def to_markdown_text() -> str:
    nb = _require_notebook_loaded()
    blocks = [
        _render_cell_block(index, cell, markdown_preview=False)
        for index, cell in enumerate(nb.cells)
    ]
    return "\n\n".join(blocks)


def from_markdown_file(path: str) -> dict[str, object]:
    nb = _require_notebook_loaded()

    try:
        markdown_content = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ToolError(f"Markdown file not found: '{path}'.") from exc
    except Exception as exc:
        raise ToolError(f"Failed to read markdown file '{path}': {exc}") from exc

    parsed_cells = _parse_markdown_document(markdown_content)
    nb.cells = parsed_cells
    session.dirty = True
    return {"path": path, "replaced": True, "cells": len(parsed_cells)}
