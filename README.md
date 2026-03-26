# jupyter-notebook-mcp

A FastMCP server for loading, reading, editing, searching, and saving Jupyter notebooks (`.ipynb`) through MCP tools.

The server keeps one notebook open at a time and uses live cell indices that update as cells are inserted or removed.

## Features

- Single active notebook session with in-memory state (`path`, notebook object, dirty flag)
- Autosave current notebook before loading a different notebook
- Real insert/remove semantics: indices shift immediately after edits
- Read full notebook as plain-text blocks
- Save/import notebook content in markdown block format
- Case-insensitive keyword search with contextual snippets
- Actionable `ToolError` messages for common failure cases

## Tool API

The server exposes the following MCP tools:

- `load_notebook(path: str)`
  - Loads and validates a notebook
  - Autosaves the currently open notebook first (if any)
- `save_notebook(path: str | None = None)`
  - Saves current notebook (optionally to a new path)
- `read_notebook()`
  - Returns active cells as plain-text blocks: `[index:N type:...]` + full content
- `read_cell(index: int)`
  - Returns full source for one active cell
- `add_cell(content: str, cell_type: str = "code", index: int | None = None)`
  - Appends a new cell when `index` is omitted
  - Inserts below the referenced cell when `index` is provided (insert at `index + 1`)
  - Returns plain-text blocks for changed cell + adjacent cells
- `replace_cell(index: int, content: str)`
  - Replaces entire cell source
- `remove_cell(index: int)`
  - Removes a cell by index with immediate reindexing
  - Returns plain-text blocks for changed cell + adjacent cells
- `delete_cell(index: int)`
  - Backward-compatible alias of `remove_cell`
- `save_markdown(path: str)`
  - Saves the same text returned by `read_notebook()` to a markdown file path
- `from_markdown(path: str)`
  - Reads exported markdown blocks from disk and replaces current notebook cells
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
uv run python -m jupyter_notebook_mcp
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
uv run python -m py_compile jupyter_notebook_mcp/*.py tests/*.py
```

Run tests:

```bash
uv run pytest -v
```

## Project Structure

```text
jupyter-notebook-mcp/
|- jupyter_notebook_mcp/
|  |- __main__.py                  # Module entrypoint for `python -m jupyter_notebook_mcp`
|  |- server.py                    # FastMCP app and tool registration
|  |- session.py                   # Shared in-memory notebook session state
|  |- notebook_io.py               # Notebook load/save and validation
|  |- cell_ops.py                  # Cell read/edit operations
|  |- markdown_codec.py            # Markdown export/import parsing
|  |- search.py                    # Keyword search and snippet extraction
|  \- formatting.py                # Cell block and markdown preview formatting
\- tests/
   |- conftest.py                  # Shared fixtures (session reset)
   |- helpers.py                   # Shared notebook test helpers
   |- test_contract_flow.py
   |- test_session_and_io.py
   |- test_cell_editing.py
   |- test_markdown_codec.py
   \- test_search_and_formatting.py
```

## Behavior Notes

- If no notebook is loaded, notebook-dependent tools return:
  - `No notebook is loaded. Use load_notebook(path) first.`
- Cell indices are always current active indices; insert/remove operations reindex following cells.
- On save, the server validates notebook structure with `nbformat.validate` before writing.
