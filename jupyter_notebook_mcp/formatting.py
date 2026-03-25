from nbformat.notebooknode import NotebookNode


def _format_markdown_preview(source: str, char_limit: int = 240) -> str:
    normalized = " ".join(source.split())
    if len(normalized) <= char_limit:
        return normalized

    truncated = normalized[:char_limit].rstrip()
    return f"{truncated} ..."


def _format_cell_block(index: int, cell_type: str, source: str) -> str:
    return f"[index:{index} type:{cell_type}]\n\n{source}"


def _render_cell_block(
    index: int, cell: NotebookNode, *, markdown_preview: bool
) -> str:
    source = str(cell.source)
    if markdown_preview and cell.cell_type == "markdown":
        source = _format_markdown_preview(source)
    return _format_cell_block(index=index, cell_type=cell.cell_type, source=source)
