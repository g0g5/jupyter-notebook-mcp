## Project Overview
This project is a Python 3.12 FastMCP server that loads, reads, edits, searches, and saves Jupyter notebooks via MCP tools.

## Structure Map
jupyter-notebook-mcp/
|- main.py                  # MCP server entrypoint with notebook session state and tool implementations
\- tests/                   # Unittest-based contract tests for tool behavior and error handling

## Development Guide
- Install/update dependencies: `uv sync`
- Run the server locally: `uv run python main.py`
- Run tests: `uv run python -m unittest discover -s tests -p "test_*.py" -v`
- Typecheck (lightweight, no dedicated type checker configured): `uv run python -m py_compile main.py tests/test_phase5.py`
- Verify changes before handoff: run the typecheck command, then run the test command
