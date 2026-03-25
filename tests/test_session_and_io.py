from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from fastmcp.exceptions import ToolError
import nbformat
import pytest

import main

from tests.helpers import write_notebook


def test_standardized_errors_for_contract_failures(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as err:
        main.read_cell(0)
    assert str(err.value) == "No notebook is loaded. Use load_notebook(path) first."

    notebook_path = tmp_path / "errors.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    with pytest.raises(ToolError) as err:
        main.read_cell(-1)
    assert str(err.value) == "Cell index -1 is out of range."

    main.remove_cell(2)
    with pytest.raises(ToolError) as err:
        main.remove_cell(2)
    assert str(err.value) == "Cell index 2 is out of range."

    invalid_path = tmp_path / "invalid.ipynb"
    invalid_path.write_text('{"nbformat": 4, "cells": "bad"}', encoding="utf-8")
    with pytest.raises(ToolError) as err:
        main.load_notebook(str(invalid_path))
    assert "Invalid notebook file" in str(err.value)


def test_autosave_failure_is_actionable(tmp_path: Path) -> None:
    first_path = tmp_path / "first.ipynb"
    second_path = tmp_path / "second.ipynb"
    write_notebook(first_path)
    write_notebook(second_path)
    main.load_notebook(str(first_path))

    with patch(
        "jupyter_notebook_mcp.notebook_io.nbformat.write",
        side_effect=RuntimeError("disk full"),
    ):
        with pytest.raises(ToolError) as err:
            main.load_notebook(str(second_path))

    assert "Autosave failed" in str(err.value)
    assert "disk full" in str(err.value)


def test_load_notebook_file_not_found_has_actionable_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.ipynb"

    with pytest.raises(ToolError) as err:
        main.load_notebook(str(missing_path))

    message = str(err.value)
    assert "Notebook file not found" in message
    assert str(missing_path) in message


def test_save_notebook_without_loaded_notebook_fails() -> None:
    with pytest.raises(ToolError) as err:
        main.save_notebook()
    assert str(err.value) == "No notebook is loaded. Use load_notebook(path) first."


def test_save_notebook_validation_failure_is_actionable(tmp_path: Path) -> None:
    notebook_path = tmp_path / "validation.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    with patch(
        "jupyter_notebook_mcp.notebook_io.nbformat.validate",
        side_effect=ValueError("bad schema"),
    ):
        with pytest.raises(ToolError) as err:
            main.save_notebook()

    assert str(err.value) == "Save failed: notebook is invalid: bad schema"


def test_load_notebook_autosaves_dirty_changes_before_switching(tmp_path: Path) -> None:
    first_path = tmp_path / "autosave-first.ipynb"
    second_path = tmp_path / "autosave-second.ipynb"
    write_notebook(first_path)
    write_notebook(second_path)

    main.load_notebook(str(first_path))
    main.replace_cell(1, "print('autosaved update')")
    main.remove_cell(2)

    loaded = cast(dict[str, Any], main.load_notebook(str(second_path)))
    assert loaded["path"] == str(second_path)
    assert main.session.path == str(second_path)
    assert main.session.dirty is False

    autosaved_first = nbformat.read(first_path, as_version=4)
    assert len(autosaved_first.cells) == 2
    assert "autosaved update" in str(autosaved_first.cells[1].source)
