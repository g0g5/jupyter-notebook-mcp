from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastmcp.exceptions import ToolError
import nbformat

import main


def _reset_session() -> None:
    main.session.path = None
    main.session.nb = None
    main.session.deleted_indices.clear()
    main.session.dirty = False


def _write_notebook(path: Path) -> None:
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(
                "one two three four five six seven eight nine ten eleven"
            ),
            nbformat.v4.new_code_cell("print('hello world')\nvalue = 10"),
            nbformat.v4.new_raw_cell("raw payload"),
        ]
    )
    nbformat.write(notebook, path)


class Phase5ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_session()

    def tearDown(self) -> None:
        _reset_session()

    def test_end_to_end_flow_and_reload_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            notebook_path = Path(tmp_dir) / "flow.ipynb"
            _write_notebook(notebook_path)

            loaded = main.load_notebook(str(notebook_path))
            self.assertEqual(
                set(loaded), {"path", "total_cells", "active_cells", "deleted_indices"}
            )
            self.assertEqual(loaded["total_cells"], 3)
            self.assertEqual(loaded["active_cells"], 3)
            self.assertEqual(loaded["deleted_indices"], [])

            outline = main.read_outline()
            self.assertEqual(set(outline), {"path", "cells"})
            self.assertEqual(outline["cells"][0]["index"], 0)
            self.assertEqual(
                outline["cells"][0]["preview"],
                "one two three four five six seven eight nine ten ...",
            )
            self.assertEqual(outline["cells"][1]["preview"], "[code cell]")
            self.assertEqual(outline["cells"][2]["preview"], "[raw cell]")

            search = main.search_cell("hello")
            self.assertEqual(set(search), {"keywords", "results"})
            self.assertEqual(search["keywords"], ["hello"])
            self.assertEqual(search["results"][0]["index"], 1)
            self.assertTrue(search["results"][0]["snippets"])

            edited = main.edit_cell(1, "print('hello edited')")
            self.assertEqual(set(edited), {"index", "updated", "chars"})
            self.assertEqual(edited["index"], 1)
            self.assertTrue(edited["updated"])

            deleted = main.delete_cell(0)
            self.assertEqual(set(deleted), {"index", "deleted"})
            self.assertEqual(deleted["index"], 0)
            self.assertTrue(deleted["deleted"])

            with self.assertRaises(ToolError) as err:
                main.read_cell(0)
            self.assertIn("has been deleted", str(err.exception))

            save_result = main.save_notebook()
            self.assertEqual(set(save_result), {"path", "saved", "active_cells"})
            self.assertEqual(save_result["active_cells"], 2)

            reloaded = main.load_notebook(str(notebook_path))
            self.assertEqual(reloaded["total_cells"], 2)

    def test_standardized_errors_for_contract_failures(self) -> None:
        with self.assertRaises(ToolError) as err:
            main.read_cell(0)
        self.assertEqual(
            str(err.exception),
            "No notebook is loaded. Use load_notebook(path) first.",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            notebook_path = Path(tmp_dir) / "errors.ipynb"
            _write_notebook(notebook_path)
            main.load_notebook(str(notebook_path))

            with self.assertRaises(ToolError) as err:
                main.read_cell(-1)
            self.assertEqual(str(err.exception), "Cell index -1 is out of range.")

            main.delete_cell(2)
            with self.assertRaises(ToolError) as err:
                main.delete_cell(2)
            self.assertEqual(str(err.exception), "Cell index 2 is already deleted.")

            invalid_path = Path(tmp_dir) / "invalid.ipynb"
            invalid_path.write_text('{"nbformat": 4, "cells": "bad"}', encoding="utf-8")
            with self.assertRaises(ToolError) as err:
                main.load_notebook(str(invalid_path))
            self.assertIn("Invalid notebook file", str(err.exception))

    def test_autosave_failure_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_path = Path(tmp_dir) / "first.ipynb"
            second_path = Path(tmp_dir) / "second.ipynb"
            _write_notebook(first_path)
            _write_notebook(second_path)
            main.load_notebook(str(first_path))

            with patch("main.nbformat.write", side_effect=RuntimeError("disk full")):
                with self.assertRaises(ToolError) as err:
                    main.load_notebook(str(second_path))

            self.assertIn("Autosave failed", str(err.exception))
            self.assertIn("disk full", str(err.exception))


if __name__ == "__main__":
    unittest.main()
