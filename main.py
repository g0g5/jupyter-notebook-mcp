from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
import nbformat
from nbformat.notebooknode import NotebookNode


mcp = FastMCP("jupyter-notebook-mcp", strict_input_validation=True)


@dataclass
class SessionState:
    path: str | None = None
    nb: NotebookNode | None = None
    deleted_indices: set[int] = field(default_factory=set)
    dirty: bool = False


session = SessionState()

WORD_RE = re.compile(r"\S+")


def _not_loaded_error() -> ToolError:
    return ToolError("No notebook is loaded. Use load_notebook(path) first.")


def _out_of_range_error(index: int) -> ToolError:
    return ToolError(f"Cell index {index} is out of range.")


def _deleted_index_error(index: int) -> ToolError:
    return ToolError(f"Cell index {index} has been deleted.")


def _already_deleted_error(index: int) -> ToolError:
    return ToolError(f"Cell index {index} is already deleted.")


def _require_notebook_loaded() -> NotebookNode:
    if session.nb is None or session.path is None:
        raise _not_loaded_error()
    return session.nb


def _ensure_index_in_range(index: int, nb: NotebookNode) -> None:
    if index < 0 or index >= len(nb.cells):
        raise _out_of_range_error(index)


def _ensure_cell_not_deleted(index: int) -> None:
    if index in session.deleted_indices:
        raise _deleted_index_error(index)


def _resolve_active_cell(index: int) -> NotebookNode:
    nb = _require_notebook_loaded()

    _ensure_index_in_range(index, nb)
    _ensure_cell_not_deleted(index)

    return nb.cells[index]


def _format_markdown_preview(source: str, word_limit: int = 10) -> str:
    words = source.split()
    if len(words) <= word_limit:
        return " ".join(words)
    return f"{' '.join(words[:word_limit])} ..."


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


def _materialize_active_notebook(nb: NotebookNode) -> NotebookNode:
    materialized = copy.deepcopy(nb)
    materialized.cells = [
        cell
        for idx, cell in enumerate(materialized.cells)
        if idx not in session.deleted_indices
    ]
    return materialized


def _save_open_notebook(*, autosave: bool) -> dict[str, object]:
    nb = _require_notebook_loaded()
    assert session.path is not None

    try:
        materialized = _materialize_active_notebook(nb)
        nbformat.validate(materialized)
    except Exception as exc:
        operation = "Autosave" if autosave else "Save"
        raise ToolError(f"{operation} failed: notebook is invalid: {exc}") from exc

    try:
        nbformat.write(materialized, session.path)
    except Exception as exc:
        operation = "Autosave" if autosave else "Save"
        raise ToolError(f"{operation} failed for '{session.path}': {exc}") from exc

    session.dirty = False
    return {
        "path": session.path,
        "saved": True,
        "active_cells": len(materialized.cells),
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
    session.deleted_indices.clear()
    session.dirty = False

    total_cells = len(loaded_nb.cells)
    return {
        "path": path,
        "total_cells": total_cells,
        "active_cells": total_cells,
        "deleted_indices": [],
    }


@mcp.tool
def save_notebook() -> dict[str, object]:
    return _save_open_notebook(autosave=False)


@mcp.tool
def read_outline() -> dict[str, object]:
    nb = _require_notebook_loaded()
    assert session.path is not None

    cells: list[dict[str, object]] = []
    for index, cell in enumerate(nb.cells):
        if index in session.deleted_indices:
            continue

        cell_type = cell.cell_type
        if cell_type == "markdown":
            preview = _format_markdown_preview(str(cell.source))
        elif cell_type == "code":
            preview = "[code cell]"
        else:
            preview = "[raw cell]"

        cells.append({"index": index, "type": cell_type, "preview": preview})

    return {"path": session.path, "cells": cells}


@mcp.tool
def read_cell(index: int) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    return {"index": index, "type": cell.cell_type, "source": str(cell.source)}


@mcp.tool
def edit_cell(index: int, content: str) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    cell.source = content
    session.dirty = True
    return {"index": index, "updated": True, "chars": len(content)}


@mcp.tool
def delete_cell(index: int) -> dict[str, object]:
    nb = _require_notebook_loaded()

    _ensure_index_in_range(index, nb)
    if index in session.deleted_indices:
        raise _already_deleted_error(index)

    session.deleted_indices.add(index)
    session.dirty = True
    return {"index": index, "deleted": True}


@mcp.tool
def search_cell(keywords: str) -> dict[str, object]:
    nb = _require_notebook_loaded()

    parsed_keywords = keywords.split()
    if not parsed_keywords:
        return {"keywords": [], "results": []}

    lowered_keywords = [keyword.lower() for keyword in parsed_keywords]

    results: list[dict[str, object]] = []
    for index, cell in enumerate(nb.cells):
        if index in session.deleted_indices:
            continue

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
