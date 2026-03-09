"""Unit tests for runicorn.assets.outputs_scan."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from filelock import FileLock

from runicorn.assets.archive import archive_file_overwrite as real_archive_file_overwrite
from runicorn.assets.outputs_scan import scan_outputs_once


class TestScanOutputsCancellation:
    def test_stop_request_prevents_assets_update_after_archive(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        storage_root = tmp_path / "storage"
        run_dir = storage_root / "runs" / "test" / "scan_001"
        output_dir = tmp_path / "workspace" / "outputs"
        assets_path = run_dir / "assets.json"
        state_path = run_dir / ".outputs_state.json"

        run_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_path.write_text("{}", encoding="utf-8")

        src = output_dir / "model.pth"
        src.write_bytes(b"model-data")

        stop_event = threading.Event()

        def _archive_then_stop(*args, **kwargs):
            result = real_archive_file_overwrite(*args, **kwargs)
            stop_event.set()
            return result

        monkeypatch.setattr(
            "runicorn.assets.outputs_scan.archive_file_overwrite",
            _archive_then_stop,
        )

        result = scan_outputs_once(
            run_id="scan_001",
            run_dir=run_dir,
            storage_root=storage_root,
            workspace_root=tmp_path / "workspace",
            output_dirs=[output_dir],
            assets_path=assets_path,
            assets_lock=FileLock(str(run_dir / "assets.json.lock")),
            state_path=state_path,
            state_lock=FileLock(str(run_dir / "outputs_state.lock")),
            patterns=["*.pth"],
            stable_required=1,
            min_age_sec=0,
            should_stop=stop_event.is_set,
        )

        assert result["scanned"] == 1
        assert result["archived"] == 0
        assert result["archived_entries"] == []
        assert json.loads(assets_path.read_text(encoding="utf-8")) == {}
