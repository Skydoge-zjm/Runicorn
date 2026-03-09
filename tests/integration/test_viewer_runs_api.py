"""Integration tests for /api/runs/* endpoints."""
from __future__ import annotations

import json
from typing import List

from fastapi.testclient import TestClient


# Convenient aliases for the run IDs used in the viewer fixture.
RUN_A = "20250101_120000_aaaaaa"  # cv/yolo
RUN_B = "20250102_120000_bbbbbb"  # cv/yolo, tag=baseline
RUN_C = "20250103_120000_cccccc"  # nlp/bert


class TestListRuns:

    def test_list_runs_from_sqlite(
        self, viewer_client: TestClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = viewer_client.get("/api/runs")
        assert resp.status_code == 200
        runs = resp.json()
        ids = {r["id"] for r in runs}
        assert RUN_A in ids
        assert RUN_B in ids
        assert RUN_C in ids

    def test_list_runs_has_expected_fields(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get("/api/runs")
        run = resp.json()[0]
        for key in ("id", "status", "path", "created_time"):
            assert key in run

    def test_list_runs_empty_storage(self, viewer_client: TestClient) -> None:
        """Empty DB → fallback to file scan → empty list."""
        resp = viewer_client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetRunDetail:

    def test_get_existing_run(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == RUN_A
        assert "status" in data
        # BUG-37: summary field present (from summary.json)
        assert "summary" in data
        assert isinstance(data["summary"], dict)

    def test_get_nonexistent_run(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/runs/20250101_000000_ffffff")
        assert resp.status_code == 404

    def test_get_run_detail_includes_summary(
        self, viewer_client: TestClient, populated_viewer_storage, viewer_storage_root
    ) -> None:
        """BUG-37: run.summary() data is returned in get_run_detail."""
        import json
        run_dir = viewer_storage_root / "runs" / "cv" / "yolo" / RUN_A
        summary_path = run_dir / "summary.json"
        summary_path.write_text(
            json.dumps({"final_loss": 0.01, "best_metric_name": "acc", "best_metric_value": 0.95}),
            encoding="utf-8",
        )
        resp = viewer_client.get(f"/api/runs/{RUN_A}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["final_loss"] == 0.01
        assert data["summary"]["best_metric_name"] == "acc"


class TestSoftDeleteAndRestore:

    def test_soft_delete_removes_from_list(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        assert resp.status_code == 200

        runs = viewer_client.get("/api/runs").json()
        ids = {r["id"] for r in runs}
        assert RUN_B not in ids

    def test_deleted_appears_in_recycle_bin(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        resp = viewer_client.get("/api/recycle-bin")
        assert resp.status_code == 200
        deleted_ids = {r["id"] for r in resp.json()["deleted_runs"]}
        assert RUN_B in deleted_ids

    def test_restore_run(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        resp = viewer_client.post(
            "/api/recycle-bin/restore",
            json={"run_ids": [RUN_B]},
        )
        assert resp.status_code == 200

        runs = viewer_client.get("/api/runs").json()
        ids = {r["id"] for r in runs}
        assert RUN_B in ids


class TestUpdateRun:

    def test_update_alias(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.patch(
            f"/api/runs/{RUN_A}",
            json={"alias": "best-run"},
        )
        assert resp.status_code == 200
        assert resp.json()["alias"] == "best-run"

    def test_update_tags(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.patch(
            f"/api/runs/{RUN_A}",
            json={"tags": ["v1", "production"]},
        )
        assert resp.status_code == 200
        assert set(resp.json()["tags"]) == {"v1", "production"}


class TestEmptyRecycleBin:

    def test_empty_recycle_bin(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        """Soft-delete a run, then permanently empty the recycle bin."""
        # Soft-delete first
        viewer_client.post(
            "/api/runs/soft-delete",
            json={"run_ids": [RUN_B]},
        )
        # Permanently delete
        resp = viewer_client.post(
            "/api/recycle-bin/empty",
            json={"confirm": True},
        )
        assert resp.status_code == 200
        assert resp.json()["permanently_deleted"] >= 1

        # Recycle bin should now be empty
        resp = viewer_client.get("/api/recycle-bin")
        assert resp.status_code == 200
        assert len(resp.json()["deleted_runs"]) == 0


class TestGetRunAssets:

    def test_get_run_assets(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        resp = viewer_client.get(f"/api/runs/{RUN_A}/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == RUN_A
        assert "assets" in data

    def test_get_run_assets_not_found(
        self, viewer_client: TestClient,
    ) -> None:
        resp = viewer_client.get("/api/runs/20250101_000000_ffffff/assets")
        assert resp.status_code == 404


class TestDownloadRunAssets:

    def test_downloads_archived_asset_linked_to_run(
        self,
        viewer_client: TestClient,
        populated_viewer_storage,
        viewer_storage_root,
        viewer_backend,
    ) -> None:
        run_dir = viewer_storage_root / "runs" / "cv" / "yolo" / RUN_A
        archive_path = viewer_storage_root / "archive" / "outputs" / "linked.txt"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_text("linked archive", encoding="utf-8")

        (run_dir / "assets.json").write_text(
            json.dumps(
                {
                    "outputs": [
                        {
                            "key": "outputs/linked.txt",
                            "name": "linked.txt",
                            "kind": "file",
                            "saved": True,
                            "archive_path": str(archive_path),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        viewer_backend.record_asset_for_run(
            run_id=RUN_A,
            role="output",
            asset_type="output",
            name="linked.txt",
            source_uri="./outputs/linked.txt",
            archive_uri=str(archive_path),
            is_archived=True,
            fingerprint_kind="stat",
            fingerprint="1:1",
            metadata={"key": "outputs/linked.txt", "kind": "file", "mode": "rolling"},
        )

        resp = viewer_client.get(
            f"/api/runs/{RUN_A}/assets/download",
            params={"path": str(archive_path)},
        )

        assert resp.status_code == 200
        assert resp.content == b"linked archive"

    def test_rejects_unrelated_file_under_storage_root(
        self,
        viewer_client: TestClient,
        populated_viewer_storage,
        viewer_storage_root,
    ) -> None:
        unrelated = viewer_storage_root / "runicorn.db"
        assert unrelated.exists()

        resp = viewer_client.get(
            f"/api/runs/{RUN_A}/assets/download",
            params={"path": str(unrelated)},
        )

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Path does not belong to this run"


class TestGetRunImages:

    def test_get_run_images_empty(
        self, viewer_client: TestClient, populated_viewer_storage
    ) -> None:
        """BUG-34: /runs/{id}/images returns empty list when no image events."""
        resp = viewer_client.get(f"/api/runs/{RUN_A}/images")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == RUN_A
        assert data["images"] == []

    def test_get_run_images_not_found(self, viewer_client: TestClient) -> None:
        resp = viewer_client.get("/api/runs/20250101_000000_ffffff/images")
        assert resp.status_code == 404

    def test_get_run_images_with_events(
        self, viewer_client: TestClient, populated_viewer_storage, viewer_storage_root
    ) -> None:
        """BUG-34: /runs/{id}/images returns image events from events.jsonl."""
        import json
        run_dir = viewer_storage_root / "runs" / "cv" / "yolo" / RUN_A
        media_dir = run_dir / "media"
        media_dir.mkdir(exist_ok=True)
        (media_dir / "123456_pred.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        events_path = run_dir / "events.jsonl"
        existing = events_path.read_text(encoding="utf-8").strip()
        new_line = json.dumps({
            "ts": 1704067200.0,
            "type": "image",
            "data": {"key": "prediction", "path": "media/123456_pred.png", "step": 10},
        })
        events_path.write_text((existing + "\n" + new_line + "\n") if existing else new_line + "\n")
        resp = viewer_client.get(f"/api/runs/{RUN_A}/images")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["images"]) == 1
        img = data["images"][0]
        assert img["key"] == "prediction"
        assert img["step"] == 10
        assert "123456_pred.png" in img["path"]
