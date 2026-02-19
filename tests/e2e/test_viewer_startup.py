"""E2E tests for viewer startup — create_app initialization."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastapi import FastAPI


@pytest.fixture
def viewer_app(tmp_path: Path):
    """Create a viewer FastAPI app with mocked storage."""
    mock_backend = MagicMock()
    mock_backend.close = MagicMock()

    with patch("runicorn.viewer.get_storage_root", return_value=tmp_path), \
         patch("runicorn.viewer.setup_logging"), \
         patch("runicorn.storage.backends.SQLiteStorageBackend", return_value=mock_backend), \
         patch("runicorn.viewer.periodic_status_check"):
        from runicorn.viewer import create_app
        app = create_app(storage=str(tmp_path))

    app.state.storage_backend = mock_backend
    return app


class TestViewerCreateApp:
    """create_app returns a properly configured FastAPI."""

    def test_returns_fastapi(self, viewer_app: FastAPI):
        assert isinstance(viewer_app, FastAPI)
        assert viewer_app.title == "Runicorn Viewer"

    def test_has_api_routes(self, viewer_app: FastAPI):
        paths = [r.path for r in viewer_app.routes]
        assert any("/api/health" in p for p in paths)
        assert any("/api/runs" in p for p in paths)

    def test_storage_root_set(self, viewer_app: FastAPI):
        assert hasattr(viewer_app.state, "storage_root")
        assert viewer_app.state.storage_root is not None
