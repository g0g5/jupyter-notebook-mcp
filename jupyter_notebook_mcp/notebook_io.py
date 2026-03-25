from __future__ import annotations

import nbformat
from fastmcp.exceptions import ToolError
from nbformat.notebooknode import NotebookNode

from .errors import _invalid_cell_type_error
from .session import _require_notebook_loaded, session


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


def load_notebook_impl(path: str) -> dict[str, object]:
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


def save_notebook_impl(path: str | None = None) -> dict[str, object]:
    return _save_open_notebook(autosave=False, path=path)
