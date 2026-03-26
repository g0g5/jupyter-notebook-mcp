from nbformat.notebooknode import NotebookNode


def _format_cell_block(index: int, cell_type: str, source: str) -> str:
    return f"[index:{index} type:{cell_type}]\n\n{source}"


def _render_cell_block(index: int, cell: NotebookNode) -> str:
    return _format_cell_block(
        index=index, cell_type=cell.cell_type, source=str(cell.source)
    )
