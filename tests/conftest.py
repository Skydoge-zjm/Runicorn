"""Root conftest — shared fixtures, markers and CLI options for all tests."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    # Ensure src/ is importable
    src = str(_SRC_ROOT)
    if src not in sys.path:
        sys.path.insert(0, src)

    # Register custom markers
    config.addinivalue_line("markers", "unit: unit tests (no network, no subprocess)")
    config.addinivalue_line("markers", "integration: integration tests (TestClient, no real SSH)")
    config.addinivalue_line("markers", "e2e: end-to-end tests")
    config.addinivalue_line("markers", "slow: slow-running tests")


# ---------------------------------------------------------------------------
# Re-export shared fixtures so every test file can use them directly.
# ---------------------------------------------------------------------------

from tests.fixtures.storage import storage_root, sqlite_backend, populated_storage, populated_db  # noqa: E402, F401
from tests.fixtures.config import mock_config_root  # noqa: E402, F401
from tests.fixtures.viewer import (  # noqa: E402, F401
    viewer_storage_root, viewer_backend, populated_viewer_storage,
    viewer_app, viewer_client,
)
