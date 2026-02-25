"""Tests for runicorn.storage.file_utils."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runicorn.storage.file_utils import (
    RunEntry,
    read_json,
    write_json,
    is_process_alive,
    is_run_deleted,
    soft_delete_run,
    restore_run,
    list_run_dirs_legacy,
    iter_all_runs,
    find_run_dir_by_id,
    update_status_if_process_dead,
)


# ===========================================================================
# RunEntry
# ===========================================================================

class TestRunEntry:

    def test_project_property(self) -> None:
        entry = RunEntry(path="cv/detection/yolo", dir=Path("/tmp/r"))
        assert entry.project == "cv"

    def test_name_property(self) -> None:
        entry = RunEntry(path="cv/detection/yolo", dir=Path("/tmp/r"))
        assert entry.name == "yolo"

    def test_properties_none_path(self) -> None:
        entry = RunEntry(path=None, dir=Path("/tmp/r"))
        assert entry.project is None
        assert entry.name is None


# ===========================================================================
# read_json / write_json
# ===========================================================================

class TestReadWriteJson:

    def test_read_json_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        assert read_json(f) == {"key": "value"}

    def test_read_json_missing(self, tmp_path: Path) -> None:
        assert read_json(tmp_path / "no_such.json") == {}

    def test_read_json_invalid(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        assert read_json(f) == {}

    def test_write_json(self, tmp_path: Path) -> None:
        f = tmp_path / "out.json"
        assert write_json(f, {"a": 1}) is True
        assert json.loads(f.read_text(encoding="utf-8")) == {"a": 1}

    def test_write_read_roundtrip(self, tmp_path: Path) -> None:
        f = tmp_path / "rt.json"
        data = {"nested": {"list": [1, 2, 3]}, "unicode": "你好"}
        write_json(f, data)
        assert read_json(f) == data


# ===========================================================================
# is_process_alive
# ===========================================================================

class TestIsProcessAlive:

    def test_none_pid(self) -> None:
        assert is_process_alive(None) is False

    @patch("runicorn.storage.file_utils.psutil")
    def test_alive(self, mock_psutil) -> None:
        mock_psutil.pid_exists.return_value = True
        assert is_process_alive(12345) is True

    @patch("runicorn.storage.file_utils.psutil")
    def test_dead(self, mock_psutil) -> None:
        mock_psutil.pid_exists.return_value = False
        assert is_process_alive(99999) is False


# ===========================================================================
# Soft-delete markers (file-based)
# ===========================================================================

class TestSoftDeleteRestore:

    def test_is_run_deleted_false(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run1"
        run_dir.mkdir()
        assert is_run_deleted(run_dir) is False

    def test_soft_delete_creates_marker(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "train" / "run1"
        run_dir.mkdir(parents=True)
        # write a dummy status.json so soft_delete_run can read it
        write_json(run_dir / "status.json", {"status": "running"})
        success, error, new_dir = soft_delete_run(
            run_dir, storage_root=tmp_path, reason="test",
        )
        assert success is True
        assert error is None
        assert new_dir is not None
        assert ".recycle" in new_dir.parts
        assert is_run_deleted(new_dir) is True

        marker = read_json(new_dir / ".deleted")
        assert marker["reason"] == "test"
        assert marker["original_status"] == "running"

    def test_soft_delete_infers_original_path_from_layout(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "cv" / "det" / "run2"
        run_dir.mkdir(parents=True)
        write_json(run_dir / "status.json", {"status": "finished"})

        ok, err, deleted_dir = soft_delete_run(run_dir, storage_root=tmp_path, reason="test")
        assert ok is True
        assert err is None
        assert deleted_dir is not None

        marker = read_json(deleted_dir / ".deleted")
        assert marker.get("original_path") == "cv/det"

        restored, restore_err, restored_dir = restore_run(deleted_dir, storage_root=tmp_path)
        assert restored is True
        assert restore_err is None
        assert restored_dir == (tmp_path / "runs" / "cv" / "det" / "run2")

    def test_restore_run(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "train" / "run1"
        run_dir.mkdir(parents=True)
        write_json(run_dir / "status.json", {"status": "running"})
        ok, _, deleted_dir = soft_delete_run(run_dir, storage_root=tmp_path)
        assert ok is True
        assert deleted_dir is not None
        assert ".recycle" in deleted_dir.parts

        restored, err, restored_dir = restore_run(deleted_dir, storage_root=tmp_path)
        assert restored is True
        assert err is None
        assert restored_dir is not None
        assert ".recycle" not in restored_dir.parts
        assert is_run_deleted(restored_dir) is False

    def test_restore_non_deleted(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "train" / "run1"
        run_dir.mkdir(parents=True)
        restored, _, _ = restore_run(run_dir, storage_root=tmp_path)
        assert restored is False


# ===========================================================================
# list_run_dirs_legacy
# ===========================================================================

class TestListRunDirsLegacy:

    def test_returns_sorted_dirs(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        (runs / "run_a").mkdir()
        (runs / "run_b").mkdir()

        result = list_run_dirs_legacy(tmp_path)
        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)

    def test_empty_when_no_runs_dir(self, tmp_path: Path) -> None:
        assert list_run_dirs_legacy(tmp_path) == []


# ===========================================================================
# iter_all_runs  — new layout + legacy layout
# ===========================================================================

def _make_run_dir(base: Path, meta: dict | None = None) -> Path:
    """Create a run directory with meta.json."""
    base.mkdir(parents=True, exist_ok=True)
    write_json(base / "meta.json", meta or {"id": base.name})
    return base


class TestIterAllRuns:

    def test_new_layout(self, tmp_path: Path) -> None:
        """root/runs/<path>/<run_id> should be discovered."""
        _make_run_dir(tmp_path / "runs" / "train" / "cifar" / "run_001")
        _make_run_dir(tmp_path / "runs" / "eval" / "run_002")

        entries = iter_all_runs(tmp_path)
        paths = {e.path for e in entries}
        assert "train/cifar" in paths
        assert "eval" in paths

    def test_legacy_layout(self, tmp_path: Path) -> None:
        """root/<project>/<name>/runs/<run_id> should be discovered."""
        (tmp_path / "runs").mkdir()  # new-layout root (empty)
        _make_run_dir(tmp_path / "myproj" / "exp1" / "runs" / "run_100")

        entries = iter_all_runs(tmp_path)
        assert len(entries) == 1
        assert entries[0].path == "myproj/exp1"

    def test_excludes_deleted_by_default(self, tmp_path: Path) -> None:
        rd = _make_run_dir(tmp_path / "runs" / "train" / "run_d")
        write_json(rd / "status.json", {"status": "running"})
        soft_delete_run(rd, storage_root=tmp_path)

        entries = iter_all_runs(tmp_path, include_deleted=False)
        assert len(entries) == 0

    def test_includes_deleted_when_requested(self, tmp_path: Path) -> None:
        rd = _make_run_dir(tmp_path / "runs" / "train" / "run_d")
        write_json(rd / "status.json", {"status": "running"})
        soft_delete_run(rd, storage_root=tmp_path)

        entries = iter_all_runs(tmp_path, include_deleted=True)
        assert len(entries) == 1

    def test_empty_root(self, tmp_path: Path) -> None:
        assert iter_all_runs(tmp_path) == []

    def test_mixed_layouts(self, tmp_path: Path) -> None:
        """Runs in both new and legacy layouts are discovered."""
        # New layout
        _make_run_dir(tmp_path / "runs" / "train" / "run_new_001")
        # Legacy layout
        _make_run_dir(tmp_path / "proj" / "exp" / "runs" / "run_leg_001")

        entries = iter_all_runs(tmp_path)
        ids = {e.dir.name for e in entries}
        assert "run_new_001" in ids
        assert "run_leg_001" in ids
        assert len(entries) == 2


# ===========================================================================
# find_run_dir_by_id
# ===========================================================================

class TestFindRunDirById:

    def test_found(self, tmp_path: Path) -> None:
        _make_run_dir(tmp_path / "runs" / "train" / "run_abc")
        entry = find_run_dir_by_id(tmp_path, "run_abc")
        assert entry is not None
        assert entry.dir.name == "run_abc"

    def test_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "runs").mkdir()
        assert find_run_dir_by_id(tmp_path, "ghost") is None


# ===========================================================================
# update_status_if_process_dead
# ===========================================================================

class TestUpdateStatusIfProcessDead:

    @patch("runicorn.storage.file_utils.is_process_alive", return_value=False)
    @patch("socket.gethostname", return_value="localhost")
    def test_marks_dead_process_as_failed(self, _mock_host, _mock_alive, tmp_path: Path) -> None:

        run_dir = tmp_path / "run1"
        run_dir.mkdir()
        write_json(run_dir / "meta.json", {"pid": 99999, "hostname": "localhost"})
        write_json(run_dir / "status.json", {"status": "running"})

        update_status_if_process_dead(run_dir)

        status = read_json(run_dir / "status.json")
        assert status["status"] == "failed"
        assert status["exit_reason"] == "process_not_found"

    @patch("runicorn.storage.file_utils.is_process_alive", return_value=False)
    @patch("socket.gethostname", return_value="localhost")
    def test_periodic_status_check_with_backend(
        self, _mock_host, _mock_alive, tmp_path: Path,
    ) -> None:
        """periodic_status_check with backend queries running experiments."""
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from runicorn.storage.file_utils import periodic_status_check

        run_dir = tmp_path / "run_psc"
        run_dir.mkdir()
        write_json(run_dir / "meta.json", {"pid": 99999, "hostname": "localhost"})
        write_json(run_dir / "status.json", {"status": "running"})

        mock_backend = MagicMock()
        mock_backend.get_running_experiments.return_value = [
            {"id": "run_psc", "run_dir": str(run_dir), "pid": 99999},
        ]

        async def _one_iteration():
            # periodic_status_check loops forever; cancel after first sleep
            task = asyncio.ensure_future(periodic_status_check(tmp_path, backend=mock_backend))
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(_one_iteration())
        # The function should have called get_running_experiments
        mock_backend.get_running_experiments.assert_called_once()

    def test_skips_non_running(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run2"
        run_dir.mkdir()
        write_json(run_dir / "meta.json", {"pid": 1})
        write_json(run_dir / "status.json", {"status": "finished"})

        update_status_if_process_dead(run_dir)
        assert read_json(run_dir / "status.json")["status"] == "finished"

    @patch("socket.gethostname", return_value="local-host")
    def test_skips_remote_hostname(self, _mock_host, tmp_path: Path) -> None:

        run_dir = tmp_path / "run3"
        run_dir.mkdir()
        write_json(run_dir / "meta.json", {"pid": 1, "hostname": "remote-host"})
        write_json(run_dir / "status.json", {"status": "running"})

        update_status_if_process_dead(run_dir)
        # Should remain running because hostname differs
        assert read_json(run_dir / "status.json")["status"] == "running"
