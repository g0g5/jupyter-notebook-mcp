# SPEC: jupyter-notebook-mcp-server

## Iteration Inputs
- Iteration name: `jupyter-notebook-mcp-server`
- Runtime: Python 3.11+ (repo currently 3.12)
- Project management: `uv` (dependency and environment management)
- Transport: stdio only
- Delete behavior: hide deleted cells; keep original indices stable until next load
- Search behavior: case-insensitive substring matching
- Load behavior: when loading another notebook, always save current notebook first

## Goal
Build a FastMCP server for one-open-notebook editing with tools:
`load_notebook`, `read_outline`, `search_cell`, `read_cell`, `edit_cell`, `delete_cell`, `save_notebook`.

## External Dependencies
- `fastmcp` - MCP server and tool registration
- `nbformat` - load/validate/save `.ipynb`
- `pydantic` - typed tool args/validation (directly or via FastMCP)

## Library Usage Notes (researched)

### FastMCP
```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("jupyter-notebook-mcp", strict_input_validation=True)

@mcp.tool
def read_cell(index: int) -> dict:
    if index < 0:
        raise ToolError("index must be >= 0")
    return {"index": index}

if __name__ == "__main__":
    mcp.run()  # stdio default
```

### nbformat
```python
import nbformat

nb = nbformat.read("notebook.ipynb", as_version=4)
nb.cells[0].source = "# updated"
nbformat.validate(nb)
nbformat.write(nb, "notebook.ipynb")
```

## Tool Contracts

### `load_notebook(path: str) -> dict`
- If another notebook is open, call save flow first (always), then unload old state.
- Load with `nbformat.read(path, as_version=4)`.
- Initialize stable index map from loaded order: `0..N-1`.
- Return `{path, total_cells, active_cells, deleted_indices}`.
- Errors: file not found, invalid notebook, autosave failure of previously opened notebook.

### `read_outline() -> dict`
- Return outline of active (not deleted) cells, preserving original indices.
- Markdown preview: first 10 words, then append ` ...` when truncated.
- Code preview: literal `[code cell]`.
- Raw/other preview: literal `[raw cell]`.
- Shape:
  - `{"path": str, "cells": [{"index": int, "type": str, "preview": str}]}`.

### `search_cell(keywords: str) -> dict`
- Input: space-separated keywords in one string.
- Matching: case-insensitive substring against cell source.
- A cell is returned when all keywords are present.
- For each hit, return compact snippet(s) with 2-word left/right context per match:
  - one keyword: `... word keyword word ...`
  - multiple nearby matches: `... word keyword1 keyword2 keyword3 word ...`
  - separate matches in same cell joined: `... hit1 ... hit2 ...`
- Shape:
  - `{"keywords": [...], "results": [{"index": int, "snippets": [str]}]}`.

### `read_cell(index: int) -> dict`
- Return full cell content for active cell at original index.
- Shape: `{"index": int, "type": str, "source": str}`.
- Errors: no notebook loaded, out-of-range index, deleted cell index.

### `edit_cell(index: int, content: str) -> dict`
- Replace full `source` for active cell at index.
- Mark notebook dirty.
- Shape: `{"index": int, "updated": true, "chars": int}`.
- Errors: same as `read_cell`.

### `delete_cell(index: int) -> dict`
- Soft-delete index in memory (do not renumber current session).
- Deleted cells are hidden from outline/read/search results.
- Mark notebook dirty.
- Shape: `{"index": int, "deleted": true}`.
- Errors: same as `read_cell`, plus already deleted.

### `save_notebook() -> dict`
- Materialize notebook by filtering out soft-deleted indices.
- Validate via `nbformat.validate(nb)`.
- Write to current path via `nbformat.write(nb, path)`.
- Keep current stable index map in memory until next `load_notebook`.
- Mark dirty false.
- Shape: `{"path": str, "saved": true, "active_cells": int}`.

## In-Memory Model
Use a single server-level session object:
```python
{
  "path": str | None,
  "nb": NotebookNode | None,
  "deleted_indices": set[int],
  "dirty": bool,
}
```

Index stability rule (before next load):
- indices are always from initial loaded notebook
- delete does not renumber
- read/search/outline ignore deleted indices

## Implementation Plan
1. Add dependencies using `uv` (e.g., `uv add fastmcp nbformat pydantic`) and keep `pyproject.toml` as source of truth.
2. Replace `main.py` with FastMCP stdio server and tool implementations.
3. Add shared guards/helpers:
   - require notebook loaded
   - resolve active cell by stable index
   - markdown preview formatter (10 words)
   - snippet extractor (2-word context)
4. Implement autosave-on-load switch behavior.
5. Validate save path and notebook validity errors with actionable `ToolError` messages.

## Acceptance Criteria
- Only one notebook can be open at once.
- Loading a second notebook triggers save of first notebook before unload.
- `read_outline` shows stable indices and required preview rules.
- `search_cell` is case-insensitive substring and returns compact snippets with context.
- `read_cell` returns full source by stable index.
- `edit_cell` updates source by stable index.
- `delete_cell` hides cell without renumbering until next load.
- `save_notebook` writes valid `.ipynb` with deletions applied.
