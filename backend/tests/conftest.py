from pathlib import Path

import pytest


@pytest.fixture
def sqlite_path(tmp_path: Path) -> Path:
    return tmp_path / "agent-test.sqlite3"
