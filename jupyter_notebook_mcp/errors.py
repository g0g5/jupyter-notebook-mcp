from fastmcp.exceptions import ToolError


def _not_loaded_error() -> ToolError:
    return ToolError("No notebook is loaded. Use load_notebook(path) first.")


def _out_of_range_error(index: int) -> ToolError:
    return ToolError(f"Cell index {index} is out of range.")


def _invalid_cell_type_error(cell_type: str) -> ToolError:
    return ToolError(
        f"Unsupported cell type '{cell_type}'. Use one of: code, markdown, raw."
    )
