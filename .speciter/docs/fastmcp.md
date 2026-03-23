# FastMCP: typed tools, stdio startup, and error handling

Updated from FastMCP docs (main-branch docs):
- https://gofastmcp.com/servers/tools.md
- https://gofastmcp.com/deployment/running-server.md
- https://gofastmcp.com/servers/context.md
- https://gofastmcp.com/python-sdk/fastmcp-exceptions.md

## 1) Define MCP tools with typed parameters

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from fastmcp import FastMCP

mcp = FastMCP("editor", strict_input_validation=True)

class ReplaceRequest(BaseModel):
    path: str
    find: str
    replace: str

@mcp.tool
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool
def grep_file(
    path: Annotated[str, Field(description="Repo-relative path")],
    pattern: Annotated[str, Field(min_length=1)],
    max_hits: Annotated[int, Field(ge=1, le=200)] = 50,
    mode: Literal["regex", "literal"] = "regex",
) -> list[int]:
    return []

@mcp.tool
def replace_text(req: ReplaceRequest) -> dict:
    return {"ok": True, "path": req.path}
```

## 2) Start a stdio server

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()  # stdio is default
```

```bash
python server.py
# or
fastmcp run server.py
```

## 3) Tool error handling + stateful file-edit workflow

```python
from dataclasses import dataclass
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context
from fastmcp.dependencies import CurrentContext

mcp = FastMCP("stateful-editor", mask_error_details=True)

@dataclass
class Snapshot:
    content: str
    rev: int

@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
async def open_file(path: str, ctx: Context = CurrentContext()) -> dict:
    content = "..."  # load file here
    snap = Snapshot(content=content, rev=1)
    await ctx.set_state(f"file:{path}", snap.__dict__)
    return snap.__dict__

@mcp.tool(annotations={"destructiveHint": True})
async def apply_edit(path: str, base_rev: int, find: str, replace: str, ctx: Context = CurrentContext()) -> dict:
    snap = await ctx.get_state(f"file:{path}")
    if not snap:
        raise ToolError("No open snapshot. Call open_file first.")
    if base_rev != snap["rev"]:
        raise ToolError(f"Revision mismatch: expected {snap['rev']}, got {base_rev}. Re-open and retry.")
    if find not in snap["content"]:
        raise ToolError("Target text not found; edit not applied.")

    new_content = snap["content"].replace(find, replace, 1)
    # persist new_content to disk here
    next_snap = {"content": new_content, "rev": snap["rev"] + 1}
    await ctx.set_state(f"file:{path}", next_snap)
    return {"ok": True, "path": path, "rev": next_snap["rev"]}
```

Notes:
- `mask_error_details=True` hides non-`ToolError` internals from clients.
- `ToolError` is for user-facing, actionable failures.
- Session state (`ctx.get_state` / `ctx.set_state`) enables optimistic-concurrency edit loops.
