"""Unit-test conftest — auto-apply @pytest.mark.unit to all tests here."""
from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
