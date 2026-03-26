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
    return load_notebook_impl(path)


@mcp.tool
def save_notebook(path: str | None = None) -> dict[str, object]:
    return save_notebook_impl(path)


@mcp.tool
def read_notebook() -> str:
    return read_notebook_text()


@mcp.tool
def read_cell(index: int) -> dict[str, object]:
    return read_cell_impl(index)


@mcp.tool
def add_cell(content: str, cell_type: str = "code", index: int | None = None) -> str:
    return add_cell_impl(content, cell_type=cell_type, index=index)


@mcp.tool
def replace_cell(index: int, content: str) -> dict[str, object]:
    return replace_cell_impl(index, content)


@mcp.tool
def remove_cell(index: int) -> str:
    return remove_cell_impl(index)


@mcp.tool
def delete_cell(index: int) -> str:
    return remove_cell_impl(index)


@mcp.tool
def save_markdown(path: str) -> dict[str, object]:
    return save_markdown_file(path)


@mcp.tool
def from_markdown(path: str) -> dict[str, object]:
    return from_markdown_file(path)


@mcp.tool
def search_cell(keywords: str) -> dict[str, object]:
    return search_cells(keywords)


def main() -> None:
    mcp.run()
