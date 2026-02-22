"""Integration-test conftest — auto-apply @pytest.mark.integration."""
from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
