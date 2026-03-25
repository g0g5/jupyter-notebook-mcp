from __future__ import annotations

from .formatting import _render_cell_block
from .notebook_io import _new_cell
from .session import (
    _ensure_index_in_range,
    _require_notebook_loaded,
    _resolve_active_cell,
    session,
)


def read_outline_impl() -> str:
    nb = _require_notebook_loaded()

    blocks: list[str] = []
    for index, cell in enumerate(nb.cells):
        blocks.append(_render_cell_block(index, cell, markdown_preview=True))

    return "\n\n".join(blocks)


def read_cell_impl(index: int) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    return {"index": index, "type": cell.cell_type, "source": str(cell.source)}


def add_cell_impl(
    content: str, cell_type: str = "code", index: int | None = None
) -> str:
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


def replace_cell_impl(index: int, content: str) -> dict[str, object]:
    cell = _resolve_active_cell(index)
    cell.source = content
    session.dirty = True
    return {"index": index, "updated": True, "chars": len(content)}


def remove_cell_impl(index: int) -> str:
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
