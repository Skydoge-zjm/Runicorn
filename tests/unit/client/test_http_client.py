"""Unit tests for runicorn.client.http — RF-08 core verification.

All HTTP I/O is mocked via ``unittest.mock`` so no network is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from runicorn.client.exceptions import (
    BadRequestError,
    ConnectionError as APIConnectionError,
    NotFoundError,
    ServerError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_data=None, content: bytes = b"",
                   text: str = ""):
    """Build a fake ``requests.Response``-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = content
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        import requests
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


def _make_client(mock_session):
    """Instantiate RunicornClient with a pre-mocked session.

    The health-check in ``__init__`` is satisfied by returning ``{"status": "ok"}``.
    """
    # session.get is used by _verify_connection
    health_resp = _mock_response(200, {"status": "ok"})
    mock_session.get.return_value = health_resp

    with patch("runicorn.client.http.requests.Session", return_value=mock_session):
        from runicorn.client.http import RunicornClient
        client = RunicornClient(base_url="http://test:9999", timeout=5, max_retries=0)
    return client


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """A mock ``requests.Session`` shared across tests."""
    session = MagicMock()
    session.mount = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def client(mock_session):
    """RunicornClient wired to *mock_session*."""
    return _make_client(mock_session)


# ---------------------------------------------------------------------------
# Tests — API methods
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """test_health_check — GET /api/health."""

    def test_returns_status_ok(self, client, mock_session):
        mock_session.request.return_value = _mock_response(200, {"status": "ok"})
        result = client.health_check()
        assert result == {"status": "ok"}
        mock_session.request.assert_called_once()
        call_kwargs = mock_session.request.call_args
        assert "/api/health" in call_kwargs.kwargs.get("url", call_kwargs[1].get("url", ""))


class TestListRuns:
    """test_list_runs — GET /api/runs."""

    def test_returns_run_list(self, client, mock_session):
        runs = [{"id": "r1", "status": "finished"}, {"id": "r2", "status": "running"}]
        mock_session.request.return_value = _mock_response(200, runs)
        result = client.list_runs()
        assert len(result) == 2
        assert result[0]["id"] == "r1"


class TestGetRunDetail:
    """test_get_run_detail — GET /api/runs/{id}."""

    def test_returns_run_record(self, client, mock_session):
        run = {"id": "abc123", "status": "finished", "path": "cv/yolo"}
        mock_session.request.return_value = _mock_response(200, run)
        result = client.get_run("abc123")
        assert result["id"] == "abc123"
        assert result["path"] == "cv/yolo"


class TestGetMetrics:
    """test_get_metrics — GET /api/runs/{id}/metrics."""

    def test_returns_metrics(self, client, mock_session):
        metrics = {"columns": ["step", "loss"], "rows": [{"step": 1, "loss": 0.5}]}
        mock_session.request.return_value = _mock_response(200, metrics)
        result = client.get_metrics("r1", downsample=100)
        assert result["columns"] == ["step", "loss"]

    def test_no_downsample(self, client, mock_session):
        mock_session.request.return_value = _mock_response(200, {"columns": [], "rows": []})
        client.get_metrics("r1")
        call_kwargs = mock_session.request.call_args
        # params should not contain 'downsample'
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params is None or "downsample" not in (params or {})


class TestExportCsv:
    """test_export_csv — GET /api/export/{id}/csv (uses session.get directly)."""

    def test_returns_bytes(self, client, mock_session):
        csv_data = b"step,loss\n1,0.5\n2,0.3\n"
        mock_session.get.return_value = _mock_response(200, content=csv_data)
        result = client.export_csv("r1")
        assert result == csv_data


class TestExportReport:
    """test_export_report — GET /api/export/{id}/report."""

    def test_returns_report_bytes(self, client, mock_session):
        report = b"# Report\nMetrics summary"
        mock_session.get.return_value = _mock_response(200, content=report)
        result = client.export_report("r1", format="markdown")
        assert result == report


class TestSetUserRootDir:
    """test_set_user_root_dir — POST /api/config/user_root_dir."""

    def test_posts_path(self, client, mock_session):
        mock_session.request.return_value = _mock_response(200, {"path": "/new/root"})
        result = client.set_user_root_dir("/new/root")
        assert result["path"] == "/new/root"


class TestGetGpuInfo:
    """test_get_gpu_info — GET /api/gpu/telemetry."""

    def test_returns_gpu_data(self, client, mock_session):
        gpu = {"gpus": [{"name": "RTX 4090", "utilization": 80}]}
        mock_session.request.return_value = _mock_response(200, gpu)
        result = client.get_gpu_info()
        assert result["gpus"][0]["name"] == "RTX 4090"


class TestListPaths:
    """test_list_paths — GET /api/paths."""

    def test_returns_paths(self, client, mock_session):
        paths = {"paths": ["cv/yolo", "nlp/bert"], "tree": {}}
        mock_session.request.return_value = _mock_response(200, paths)
        result = client.list_paths(include_stats=True)
        assert "cv/yolo" in result["paths"]


class TestGetStorageStats:
    """test_get_storage_stats — GET /api/storage/stats."""

    def test_returns_stats(self, client, mock_session):
        stats = {"total_runs": 42, "total_size_bytes": 1024000}
        mock_session.request.return_value = _mock_response(200, stats)
        result = client.get_storage_stats()
        assert result["total_runs"] == 42


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------

class TestApiErrorHandling:
    """test_api_error_handling — 4xx/5xx responses raise typed exceptions."""

    def test_404_raises_not_found(self, client, mock_session):
        mock_session.request.return_value = _mock_response(404, text="not found")
        with pytest.raises(NotFoundError):
            client.get("/api/runs/nonexistent")

    def test_400_raises_bad_request(self, client, mock_session):
        mock_session.request.return_value = _mock_response(400, text="bad params")
        with pytest.raises(BadRequestError):
            client.post("/api/config/user_root_dir", json={})

    def test_500_raises_server_error(self, client, mock_session):
        mock_session.request.return_value = _mock_response(500, text="internal error")
        with pytest.raises(ServerError):
            client.get("/api/runs")

    def test_connection_error_wrapped(self, client, mock_session):
        import requests
        mock_session.request.side_effect = requests.ConnectionError("refused")
        with pytest.raises(APIConnectionError):
            client.get("/api/health")


class TestConnectionVerifyFails:
    """test_connection_verify_fails_graceful — __init__ raises APIConnectionError."""

    def test_unhealthy_status(self):
        session = MagicMock()
        session.mount = MagicMock()
        session.get.return_value = _mock_response(200, {"status": "degraded"})

        with patch("runicorn.client.http.requests.Session", return_value=session):
            from runicorn.client.http import RunicornClient
            with pytest.raises(APIConnectionError, match="not healthy"):
                RunicornClient(base_url="http://bad:9999")

    def test_network_failure(self):
        import requests
        session = MagicMock()
        session.mount = MagicMock()
        session.get.side_effect = requests.ConnectionError("refused")

        with patch("runicorn.client.http.requests.Session", return_value=session):
            from runicorn.client.http import RunicornClient
            with pytest.raises(APIConnectionError, match="Failed to connect"):
                RunicornClient(base_url="http://dead:9999")


# ---------------------------------------------------------------------------
# Tests — context manager & close
# ---------------------------------------------------------------------------

class TestClientLifecycle:
    """Context manager and close() behaviour."""

    def test_close_calls_session_close(self, client, mock_session):
        client.close()
        mock_session.close.assert_called_once()

    def test_context_manager(self, mock_session):
        c = _make_client(mock_session)
        with c as ctx:
            assert ctx is c
        mock_session.close.assert_called_once()

    def test_remote_property_lazy(self, client):
        remote = client.remote
        from runicorn.client.remote import RemoteAPI
        assert isinstance(remote, RemoteAPI)
        assert client.remote is remote  # same instance on second access
