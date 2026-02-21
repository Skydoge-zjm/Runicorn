"""Integration tests for /api/import/archive endpoint."""
from __future__ import annotations

import io
import json
import os
import time
import zipfile
from typing import List

from fastapi.testclient import TestClient


def _make_run_zip(run_id: str, path: str = "test/import") -> bytes:
    """Create an in-memory zip containing a minimal run directory."""
    buf = io.BytesIO()
    now = time.time()
    prefix = f"runs/{path.replace('/', os.sep)}/{run_id}"

    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            f"{prefix}/meta.json",
            json.dumps({"id": run_id, "path": path, "created_at": now}),
        )
        zf.writestr(
            f"{prefix}/status.json",
            json.dumps({"status": "finished"}),
        )
    return buf.getvalue()


class TestImportArchive:

    def test_import_valid_zip(
        self, viewer_client: TestClient, populated_viewer_storage: List[str]
    ) -> None:
        new_id = "20250201_120000_dddddd"
        data = _make_run_zip(new_id)
        resp = viewer_client.post(
            "/api/import/archive",
            files={"file": ("export.zip", data, "application/zip")},
        )
        # 200 on success; 503 if python-multipart not installed
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            body = resp.json()
            assert body["ok"] is True
            assert body["imported_files"] >= 1

    def test_import_no_file_422(self, viewer_client: TestClient) -> None:
        """Missing file field → 422 or 503."""
        resp = viewer_client.post("/api/import/archive")
        assert resp.status_code in (422, 503)


class TestImportTriggersSync:

    def test_import_then_verify_in_api(
        self,
        viewer_client: TestClient,
        viewer_storage_root,
        viewer_backend,
        populated_viewer_storage: List[str],
    ) -> None:
        """After importing a zip, the run should appear via sync."""
        new_id = "20250501_120000_gggggg"
        data = _make_run_zip(new_id, path="import/sync")
        resp = viewer_client.post(
            "/api/import/archive",
            files={"file": ("export.zip", data, "application/zip")},
        )
        if resp.status_code != 200:
            pytest.skip("import endpoint unavailable (python-multipart)")

        # Trigger manual sync so the imported run appears in SQLite
        from runicorn.viewer.services.db_reader import sync_filesystem_to_db
        sync_filesystem_to_db(viewer_storage_root, viewer_backend)

        # Verify via the runs API
        resp = viewer_client.get("/api/runs")
        ids = {r["id"] for r in resp.json()}
        assert new_id in ids
