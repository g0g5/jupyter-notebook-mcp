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


def _ensure_cell_not_deleted(index: int) -> None:
    if index in session.deleted_indices:
        raise _deleted_index_error(index)


def _resolve_active_cell(index: int) -> NotebookNode:
    nb = _require_notebook_loaded()

    _ensure_index_in_range(index, nb)
    _ensure_cell_not_deleted(index)

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


def _materialize_active_notebook(nb: NotebookNode) -> NotebookNode:
    materialized = copy.deepcopy(nb)
    materialized.cells = [
        cell
        for idx, cell in enumerate(materialized.cells)
        if idx not in session.deleted_indices
    ]
    return materialized


def _new_cell(cell_type: str, content: str) -> NotebookNode:
    normalized_type = cell_type.strip().lower()
    if normalized_type == "code":
        return nbformat.v4.new_code_cell(content)
    if normalized_type == "markdown":
        return nbformat.v4.new_markdown_cell(content)
    if normalized_type == "raw":
        return nbformat.v4.new_raw_cell(content)
    raise _invalid_cell_type_error(cell_type)


def _save_open_notebook(
    *, autosave: bool, path: str | None = None
) -> dict[str, object]:
    nb = _require_notebook_loaded()
    assert session.path is not None
    target_path = path if path is not None else session.path

    try:
        materialized = _materialize_active_notebook(nb)
        nbformat.validate(materialized)
    except Exception as exc:
        operation = "Autosave" if autosave else "Save"
        raise ToolError(f"{operation} failed: notebook is invalid: {exc}") from exc

    try:
        nbformat.write(materialized, target_path)
    except Exception as exc:
        operation = "Autosave" if autosave else "Save"
        raise ToolError(f"{operation} failed for '{target_path}': {exc}") from exc

    session.path = target_path
    session.dirty = False
    return {
        "path": target_path,
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
def save_notebook(path: str | None = None) -> dict[str, object]:
    return _save_open_notebook(autosave=False, path=path)


@mcp.tool
def read_outline() -> str:
    nb = _require_notebook_loaded()

    blocks: list[str] = []
    for index, cell in enumerate(nb.cells):
        if index in session.deleted_indices:
            continue

        cell_type = cell.cell_type
        if cell_type == "markdown":
            content = _format_markdown_preview(str(cell.source))
        else:
            content = str(cell.source)

        blocks.append(f"[index:{index} type:{cell_type}]\n\n{content}")

    return "\n\n".join(blocks)


@mcp.tool
def read_cell(index: int) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    return {"index": index, "type": cell.cell_type, "source": str(cell.source)}


@mcp.tool
def add_cell(content: str, cell_type: str = "code") -> dict[str, object]:
    nb = _require_notebook_loaded()
    cell = _new_cell(cell_type, content)
    nb.cells.append(cell)
    index = len(nb.cells) - 1
    session.dirty = True
    return {
        "index": index,
        "type": cell.cell_type,
        "added": True,
        "chars": len(content),
    }


@mcp.tool
def replace_cell(index: int, content: str) -> dict[str, object]:
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
