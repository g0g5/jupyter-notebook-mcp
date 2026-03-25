from __future__ import annotations

from typing import Generator

import pytest

from jupyter_notebook_mcp.session import session


def _reset_session() -> None:
    session.path = None
    session.nb = None
    session.dirty = False


@pytest.fixture(autouse=True)
def reset_session_fixture() -> Generator[None, None, None]:
    _reset_session()
    yield
    _reset_session()
