# PLAN: jupyter-notebook-mcp-server

## Phase 1: Project and Runtime Setup
1. Add and lock required dependencies with `uv`: `fastmcp`, `nbformat`, and `pydantic`.
2. Ensure `pyproject.toml` is the source of truth for runtime and package requirements.
3. Confirm the server entrypoint (`main.py`) is prepared to run as a stdio FastMCP service.

## Phase 2: Server Skeleton and Session State
1. Initialize a `FastMCP` server with strict input validation enabled.
2. Implement a single server-level session object with `path`, `nb`, `deleted_indices`, and `dirty`.
3. Add shared guards/helpers for:
   - notebook-loaded checks,
   - stable-index resolution for active cells,
   - markdown preview formatting (first 10 words + ` ...` when truncated),
   - search snippet extraction with 2-word context windows.

## Phase 3: Notebook Lifecycle Tools
1. Implement `load_notebook(path)` to always attempt save of the currently open notebook before switching.
2. Load notebooks via `nbformat.read(path, as_version=4)` and initialize stable indices from original load order.
3. Reset runtime state for a newly loaded notebook (`deleted_indices` cleared, `dirty` false) and return required metadata.
4. Implement `save_notebook()` to materialize a filtered notebook (excluding soft-deleted indices), validate with `nbformat.validate`, and write with `nbformat.write`.
5. Keep in-memory stable index behavior intact after save until the next load operation.

## Phase 4: Cell Access and Mutation Tools
1. Implement `read_outline()` to list only active cells with original indices and type-specific previews.
2. Implement `read_cell(index)` to return full content for an active cell at the stable index.
3. Implement `edit_cell(index, content)` to replace full source, update dirty state, and return update metadata.
4. Implement `delete_cell(index)` as soft-delete only, preserving index stability and hiding deleted cells from read/search/outline outputs.
5. Implement `search_cell(keywords)` to:
   - parse space-separated keywords,
   - perform case-insensitive substring matching,
   - require all keywords to be present per matched cell,
   - return compact snippets with required context and join behavior.

## Phase 5: Error Handling and Contract Validation
1. Standardize actionable `ToolError` messages for all contract failures (not loaded, out-of-range index, deleted index, already deleted, invalid notebook, save/autosave failures).
2. Verify each tool response shape matches the spec contract exactly.
3. Validate acceptance criteria with end-to-end tool flow checks: load -> read/search/edit/delete -> save -> reload behavior.
