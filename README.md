# jupyter-notebook-mcp

A FastMCP server for loading, reading, editing, searching, and saving Jupyter notebooks (`.ipynb`) through MCP tools.

The server keeps one notebook open at a time and provides stable cell indices during a session, even after deletions.

## Features

- Single active notebook session with in-memory state (`path`, notebook object, deleted indices, dirty flag)
- Autosave current notebook before loading a different notebook
- Soft-delete cells while keeping original indices stable until the next `load_notebook`
- Read outline previews for markdown/code/raw cells
- Case-insensitive keyword search with contextual snippets
- Actionable `ToolError` messages for common failure cases

## Tool API

The server exposes the following MCP tools:

- `load_notebook(path: str)`
  - Loads and validates a notebook
  - Autosaves the currently open notebook first (if any)
- `save_notebook(path: str | None = None)`
  - Saves current notebook (optionally to a new path)
  - Filters out soft-deleted cells before writing
- `read_outline()`
  - Returns active cells with index/type/preview
- `read_cell(index: int)`
  - Returns full source for one active cell
- `add_cell(content: str, cell_type: str = "code")`
  - Appends a new cell (`code`, `markdown`, or `raw`)
- `replace_cell(index: int, content: str)`
  - Replaces entire cell source
- `delete_cell(index: int)`
  - Soft-deletes a cell by index
- `search_cell(keywords: str)`
  - Space-separated keyword search (all keywords must match)

## Requirements

- Python `>=3.12`
- `uv` for environment and dependency management

## MCP Installation

Run directly with `uvx` (no persistent install):

```bash
uvx jupyter-notebook-mcp --from git+https://github.com/g0g5/jupyter-notebook-mcp
```

Install as a `uv` tool:

```bash
uv tool install jupyter-notebook-mcp --from git+https://github.com/g0g5/jupyter-notebook-mcp
```

## Quick Start

```bash
uv sync
uv run python main.py
```

You can also run via the project script entrypoint:

```bash
uv run jupyter-notebook-mcp
```

## MCP Client Configuration (stdio)

Use one of the following configurations.

Option 1: run with `uvx` from GitHub:

```json
{
  "mcpServers": {
    "jupyter-notebook-mcp": {
      "command": "uvx",
      "args": [
        "jupyter-notebook-mcp",
        "--from",
        "git+https://github.com/g0g5/jupyter-notebook-mcp"
      ]
    }
  }
}
```

Option 2: after `uv tool install`, run installed command directly:

```json
{
  "mcpServers": {
    "jupyter-notebook-mcp": {
      "command": "jupyter-notebook-mcp",
      "args": []
    }
  }
}
```

## Development

Install/update dependencies:

```bash
uv sync
```

Typecheck (lightweight compile check):

```bash
uv run python -m py_compile main.py tests/test_phase5.py
```

Run tests:

```bash
uv run pytest -v
```

## Project Structure

```text
jupyter-notebook-mcp/
|- main.py                  # FastMCP server and tool implementations
\- tests/
   \- test_phase5.py        # Contract and error handling tests
```

## Behavior Notes

- If no notebook is loaded, notebook-dependent tools return:
  - `No notebook is loaded. Use load_notebook(path) first.`
- Deleted cells are hidden from outline/read/search, but index numbers remain stable in the current session.
- On save, the server validates notebook structure with `nbformat.validate` before writing.
