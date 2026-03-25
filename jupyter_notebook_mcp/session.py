from __future__ import annotations

from dataclasses import dataclass

from nbformat.notebooknode import NotebookNode

from .errors import _not_loaded_error, _out_of_range_error


@dataclass
class SessionState:
    path: str | None = None
    nb: NotebookNode | None = None
    dirty: bool = False


session = SessionState()


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
