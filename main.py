from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
import nbformat
from nbformat.notebooknode import NotebookNode


mcp = FastMCP("jupyter-notebook-mcp", strict_input_validation=True)


@dataclass
class SessionState:
    path: str | None = None
    nb: NotebookNode | None = None
    dirty: bool = False


session = SessionState()

WORD_RE = re.compile(r"\S+")
CELL_HEADER_RE = re.compile(r"^\[index:(\d+) type:(code|markdown|raw)\]$")


def _not_loaded_error() -> ToolError:
    return ToolError("No notebook is loaded. Use load_notebook(path) first.")


def _out_of_range_error(index: int) -> ToolError:
    return ToolError(f"Cell index {index} is out of range.")


def _invalid_cell_type_error(cell_type: str) -> ToolError:
    return ToolError(
        f"Unsupported cell type '{cell_type}'. Use one of: code, markdown, raw."
    )


def _require_notebook_loaded() -> NotebookNode:
    if session.nb is None or session.path is None:
        raise _not_loaded_error()
    return session.nb


def _ensure_index_in_range(index: int, nb: NotebookNode) -> None:
    if index < 0 or index >= len(nb.cells):
        raise _out_of_range_error(index)


def _resolve_active_cell(index: int) -> NotebookNode:
    nb = _require_notebook_loaded()

    _ensure_index_in_range(index, nb)

    return nb.cells[index]


def _format_markdown_preview(source: str, char_limit: int = 240) -> str:
    normalized = " ".join(source.split())
    if len(normalized) <= char_limit:
        return normalized

    truncated = normalized[:char_limit].rstrip()
    return f"{truncated} ..."


def _extract_search_snippets(
    source: str,
    keywords: list[str],
    context_words: int = 2,
) -> list[str]:
    if not source or not keywords:
        return []

    lowered_source = source.lower()
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    if not lowered_keywords:
        return []

    matches: list[tuple[int, int]] = []
    for keyword in lowered_keywords:
        start = 0
        while True:
            found = lowered_source.find(keyword, start)
            if found == -1:
                break
            matches.append((found, found + len(keyword)))
            start = found + 1

    if not matches:
        return []

    word_spans = [(match.start(), match.end()) for match in WORD_RE.finditer(source)]
    if not word_spans:
        return []

    expanded_ranges: list[tuple[int, int]] = []
    for start, end in sorted(matches):
        overlapping_word_indices = [
            i
            for i, (word_start, word_end) in enumerate(word_spans)
            if not (word_end <= start or word_start >= end)
        ]
        if not overlapping_word_indices:
            continue

        left_word = max(0, overlapping_word_indices[0] - context_words)
        right_word = min(
            len(word_spans) - 1, overlapping_word_indices[-1] + context_words
        )
        expanded_ranges.append((left_word, right_word))

    if not expanded_ranges:
        return []

    merged_ranges: list[tuple[int, int]] = []
    for left_word, right_word in sorted(expanded_ranges):
        if not merged_ranges:
            merged_ranges.append((left_word, right_word))
            continue

        prev_left, prev_right = merged_ranges[-1]
        if left_word <= prev_right + 1:
            merged_ranges[-1] = (prev_left, max(prev_right, right_word))
        else:
            merged_ranges.append((left_word, right_word))

    snippets: list[str] = []
    words = [source[start:end] for start, end in word_spans]
    for left_word, right_word in merged_ranges:
        snippets.append(f"... {' '.join(words[left_word : right_word + 1])} ...")

    return snippets


def _new_cell(cell_type: str, content: str) -> NotebookNode:
    normalized_type = cell_type.strip().lower()
    if normalized_type == "code":
        return nbformat.v4.new_code_cell(content)
    if normalized_type == "markdown":
        return nbformat.v4.new_markdown_cell(content)
    if normalized_type == "raw":
        return nbformat.v4.new_raw_cell(content)
    raise _invalid_cell_type_error(cell_type)


def _format_cell_block(
    index: int,
    cell_type: str,
    source: str,
) -> str:
    return f"[index:{index} type:{cell_type}]\n\n{source}"


def _render_cell_block(
    index: int,
    cell: NotebookNode,
    *,
    markdown_preview: bool,
) -> str:
    source = str(cell.source)
    if markdown_preview and cell.cell_type == "markdown":
        source = _format_markdown_preview(source)
    return _format_cell_block(index=index, cell_type=cell.cell_type, source=source)


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


def _save_open_notebook(
    *, autosave: bool, path: str | None = None
) -> dict[str, object]:
    nb = _require_notebook_loaded()
    assert session.path is not None
    target_path = path if path is not None else session.path

    try:
        nbformat.validate(nb)
    except Exception as exc:
        operation = "Autosave" if autosave else "Save"
        raise ToolError(f"{operation} failed: notebook is invalid: {exc}") from exc

    try:
        nbformat.write(nb, target_path)
    except Exception as exc:
        operation = "Autosave" if autosave else "Save"
        raise ToolError(f"{operation} failed for '{target_path}': {exc}") from exc

    session.path = target_path
    session.dirty = False
    return {
        "path": target_path,
        "saved": True,
        "active_cells": len(nb.cells),
    }


@mcp.tool
def load_notebook(path: str) -> dict[str, object]:
    if session.nb is not None and session.path is not None:
        _save_open_notebook(autosave=True)

    try:
        loaded_nb = nbformat.read(path, as_version=4)
    except FileNotFoundError as exc:
        raise ToolError(f"Notebook file not found: '{path}'.") from exc
    except Exception as exc:
        raise ToolError(f"Invalid notebook file '{path}': {exc}") from exc

    try:
        nbformat.validate(loaded_nb)
    except Exception as exc:
        raise ToolError(f"Invalid notebook file '{path}': {exc}") from exc

    session.path = path
    session.nb = loaded_nb
    session.dirty = False

    total_cells = len(loaded_nb.cells)
    return {
        "path": path,
        "total_cells": total_cells,
        "active_cells": total_cells,
    }


@mcp.tool
def save_notebook(path: str | None = None) -> dict[str, object]:
    return _save_open_notebook(autosave=False, path=path)


@mcp.tool
def read_outline() -> str:
    nb = _require_notebook_loaded()

    blocks: list[str] = []
    for index, cell in enumerate(nb.cells):
        blocks.append(_render_cell_block(index, cell, markdown_preview=True))

    return "\n\n".join(blocks)


@mcp.tool
def read_cell(index: int) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    return {"index": index, "type": cell.cell_type, "source": str(cell.source)}


@mcp.tool
def add_cell(content: str, cell_type: str = "code", index: int | None = None) -> str:
    nb = _require_notebook_loaded()
    cell = _new_cell(cell_type, content)

    if index is None:
        insert_index = len(nb.cells)
    else:
        _ensure_index_in_range(index, nb)
        insert_index = index + 1

    nb.cells.insert(insert_index, cell)
    session.dirty = True

    blocks = [
        _render_cell_block(insert_index, nb.cells[insert_index], markdown_preview=False)
    ]
    if insert_index - 1 >= 0:
        blocks.append(
            _render_cell_block(
                insert_index - 1, nb.cells[insert_index - 1], markdown_preview=False
            )
        )
    if insert_index + 1 < len(nb.cells):
        blocks.append(
            _render_cell_block(
                insert_index + 1, nb.cells[insert_index + 1], markdown_preview=False
            )
        )

    return "\n\n".join(blocks)


@mcp.tool
def replace_cell(index: int, content: str) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    cell.source = content
    session.dirty = True
    return {"index": index, "updated": True, "chars": len(content)}


@mcp.tool
def remove_cell(index: int) -> str:
    nb = _require_notebook_loaded()

    _ensure_index_in_range(index, nb)
    blocks = [_render_cell_block(index, nb.cells[index], markdown_preview=False)]
    if index - 1 >= 0:
        blocks.append(
            _render_cell_block(index - 1, nb.cells[index - 1], markdown_preview=False)
        )
    if index + 1 < len(nb.cells):
        blocks.append(
            _render_cell_block(index + 1, nb.cells[index + 1], markdown_preview=False)
        )

    nb.cells.pop(index)
    session.dirty = True

    return "\n\n".join(blocks)


@mcp.tool
def delete_cell(index: int) -> str:
    return remove_cell(index)


@mcp.tool
def to_markdown() -> str:
    nb = _require_notebook_loaded()
    blocks = [
        _render_cell_block(index, cell, markdown_preview=False)
        for index, cell in enumerate(nb.cells)
    ]
    return "\n\n".join(blocks)


@mcp.tool
def from_markdown(path: str) -> dict[str, object]:
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


@mcp.tool
def search_cell(keywords: str) -> dict[str, object]:
    nb = _require_notebook_loaded()

    parsed_keywords = keywords.split()
    if not parsed_keywords:
        return {"keywords": [], "results": []}

    lowered_keywords = [keyword.lower() for keyword in parsed_keywords]

    results: list[dict[str, object]] = []
    for index, cell in enumerate(nb.cells):
        source = str(cell.source)
        lowered_source = source.lower()
        if not all(keyword in lowered_source for keyword in lowered_keywords):
            continue

        snippets = _extract_search_snippets(source, parsed_keywords)
        results.append({"index": index, "snippets": snippets})

    return {"keywords": parsed_keywords, "results": results}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
