"""Integration tests for /api/health and /api/status/check endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:

    def test_returns_ok(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "storage" in data
        assert "version" in data

    def test_cache_stats_present(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/health")
        data = resp.json()
        cache = data["cache"]
        assert cache["enabled"] is True
        assert "hits" in cache
        assert "misses" in cache
        assert "size" in cache


class TestStatusCheck:

    def test_check_no_running(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        """With all runs finished, check returns 0 updated."""
        resp = viewer_client.post("/api/status/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checked"] == 0
        assert data["updated"] == 0

    def test_health_check_updates_dead_runs(
        self,
        viewer_client: TestClient,
        viewer_storage_root,
        viewer_backend,
        monkeypatch,
    ) -> None:
        """Status check detects dead process and updates status to failed."""
        import json, time
        from unittest.mock import patch
        from runicorn.storage.models import ExperimentRecord

        # Create a "running" run with a dead PID on disk
        run_dir = viewer_storage_root / "runs" / "test" / "dead_run_001"
        run_dir.mkdir(parents=True)
        (run_dir / "meta.json").write_text(
            json.dumps({"id": "dead_run_001", "pid": 99999, "hostname": "__test__"}),
            encoding="utf-8",
        )
        (run_dir / "status.json").write_text(
            json.dumps({"status": "running", "started_at": time.time()}),
            encoding="utf-8",
        )

        # Register it in SQLite so the backend knows about it
        exp = ExperimentRecord(
            id="dead_run_001", path="test",
            created_at=time.time(), updated_at=time.time(),
            status="running", pid=99999, run_dir=str(run_dir),
        )
        viewer_backend.create_experiment(exp)

        # Mock is_process_alive → dead, hostname → match
        with patch("runicorn.storage.file_utils.is_process_alive", return_value=False), \
             patch("socket.gethostname", return_value="__test__"):
            resp = viewer_client.post("/api/status/check")

        assert resp.status_code == 200
        data = resp.json()
        # At least one run should have been checked and updated
        assert data["updated"] >= 1

        # Verify the on-disk status was changed to failed
        disk_status = json.loads((run_dir / "status.json").read_text("utf-8"))
        assert disk_status["status"] == "failed"
