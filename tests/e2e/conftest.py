"""E2E test conftest — auto-apply @pytest.mark.e2e."""
from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
