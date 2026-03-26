from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import jupyter_notebook_mcp as main

from jupyter_notebook_mcp.search import _extract_search_snippets

from tests.helpers import write_notebook


def test_search_cell_with_empty_keywords_returns_empty_results(tmp_path: Path) -> None:
    notebook_path = tmp_path / "search-empty.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    assert main.search_cell("   ") == {"keywords": [], "results": []}


def test_search_cell_requires_all_keywords_and_respects_real_removal(
    tmp_path: Path,
) -> None:
    notebook_path = tmp_path / "search-all.ipynb"
    write_notebook(notebook_path)
    main.load_notebook(str(notebook_path))

    found = cast(dict[str, Any], main.search_cell("hello value"))
    assert found["keywords"] == ["hello", "value"]
    assert [result["index"] for result in found["results"]] == [1]

    main.remove_cell(1)
    assert main.search_cell("hello value")["results"] == []


def test_extract_search_snippets_handles_overlap_and_empty_inputs() -> None:
    source = "alpha beta gamma delta epsilon"

    snippets = _extract_search_snippets(source, ["beta", "gamma"], context_words=1)
    assert snippets == ["... alpha beta gamma delta ..."]
    assert _extract_search_snippets("", ["alpha"]) == []
    assert _extract_search_snippets(source, []) == []
    assert _extract_search_snippets(source, [""]) == []
