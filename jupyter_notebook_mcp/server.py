from fastmcp import FastMCP

from .cell_ops import (
    add_cell_impl,
    read_cell_impl,
    remove_cell_impl,
    replace_cell_impl,
)
from .markdown_codec import from_markdown_file, read_notebook_text, save_markdown_file
from .notebook_io import load_notebook_impl, save_notebook_impl
from .search import search_cells


mcp = FastMCP("jupyter-notebook-mcp", strict_input_validation=True)


@mcp.tool
def load_notebook(path: str) -> dict[str, object]:
    """Load and validate a notebook from disk.

    Autosaves the currently open notebook before switching.
    """
    return load_notebook_impl(path)


@mcp.tool
def save_notebook(path: str | None = None) -> dict[str, object]:
    """Validate and save the active notebook to current or new path."""
    return save_notebook_impl(path)


@mcp.tool
def read_notebook() -> str:
    """Return all active cells as [index:N type:T] plain-text blocks."""
    return read_notebook_text()


@mcp.tool
def read_cell(index: int) -> dict[str, object]:
    """Return one active cell by index with type and full source."""
    return read_cell_impl(index)


@mcp.tool
def add_cell(content: str, cell_type: str = "code", index: int | None = None) -> str:
    """Insert after index, or append when index is omitted.

    cell_type must be one of: code, markdown, raw.
    """
    return add_cell_impl(content, cell_type=cell_type, index=index)


@mcp.tool
def replace_cell(index: int, content: str) -> dict[str, object]:
    """Replace the full source of the cell at the given index."""
    return replace_cell_impl(index, content)


@mcp.tool
def remove_cell(index: int) -> str:
    """Remove a cell and return previews of affected neighboring cells."""
    return remove_cell_impl(index)


@mcp.tool
def delete_cell(index: int) -> str:
    """Backward-compatible alias of remove_cell(index)."""
    return remove_cell_impl(index)


@mcp.tool
def save_markdown(path: str) -> dict[str, object]:
    """Export active notebook cells to markdown block format on disk."""
    return save_markdown_file(path)


@mcp.tool
def from_markdown(path: str) -> dict[str, object]:
    """Load markdown notebook blocks from disk and replace active cells."""
    return from_markdown_file(path)


@mcp.tool
def search_cell(keywords: str) -> dict[str, object]:
    """Search cells by space-separated keywords and return matches with snippets."""
    return search_cells(keywords)


def main() -> None:
    mcp.run()
