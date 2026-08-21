"""Global pytest fixtures and environment setup."""

import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env():
    """Ensure tests run in test mode by default."""
    os.environ["TESTING"] = "1"
    yield
    os.environ["TESTING"] = "1"
