## Project Overview
This project is a Python 3.12 FastMCP server package for loading, editing, searching, and saving Jupyter notebooks through MCP tools, with a modular runtime package, a compatibility entrypoint, and pytest-based contract coverage.

## Structure Map
jupyter-notebook-mcp/
|- jupyter_notebook_mcp/    # Core runtime modules for MCP tools, session state, notebook I/O, edits, search, and formatting
|- tests/                   # Pytest suites, fixtures, and helpers for tool contracts and module behavior
|- main.py                  # Compatibility entrypoint and re-export bridge to packaged CLI runtime
\- pyproject.toml           # Project metadata, dependency groups, and CLI script registration

## Development Guide
- Install/update dependencies: `uv sync`
- Build distributables: `uv build`
- Run the server locally (packaged entrypoint): `uv run jupyter-notebook-mcp`
- Alternate local run path: `uv run python main.py`
- Typecheck (lightweight compile check): `uv run python -m py_compile main.py jupyter_notebook_mcp/*.py tests/*.py`
- Run tests: `uv run pytest -v`
- Verify changes before handoff: run the typecheck command, then run the test command
