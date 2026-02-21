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
