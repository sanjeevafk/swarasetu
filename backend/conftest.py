"""Pytest configuration: isolate API tests onto a disposable database.

DATABASE_URL must be set before any backend.app import because Settings
instances are created at module import time.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///./swarasetu_test.db"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _clean_test_db():
    db_file = Path("swarasetu_test.db")
    if db_file.exists():
        db_file.unlink()
    yield
    if db_file.exists():
        db_file.unlink()
