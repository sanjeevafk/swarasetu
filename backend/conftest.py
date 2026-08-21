"""Pytest configuration: isolate API tests onto a disposable database.

DATABASE_URL must be set before any backend.app import because Settings
instances are created at module import time.
"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
repo_root = backend_dir.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(backend_dir))

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
