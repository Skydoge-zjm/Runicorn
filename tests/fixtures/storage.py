"""Storage-related fixtures shared across test layers."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    """Create a standard storage_root directory structure.

    Yields ``tmp_path / "storage"`` with a ``runs/`` sub-directory already
    created, ready for use by SDK or storage backend tests.
    """
    root = tmp_path / "storage"
    root.mkdir()
    (root / "runs").mkdir()
    return root


@pytest.fixture
def sqlite_backend(storage_root: Path):
    """Initialise a :class:`SQLiteStorageBackend` on *storage_root*.

    The schema is applied automatically.  The backend is closed after the
    test finishes.
    """
    from runicorn.storage.backends import SQLiteStorageBackend

    backend = SQLiteStorageBackend(storage_root)
    yield backend
    backend.close()


@pytest.fixture
def populated_storage(storage_root: Path) -> Path:
    """Pre-populate *storage_root* with 3 sample runs on disk.

    Each run has ``meta.json``, ``status.json`` and ``events.jsonl``.
    Returns *storage_root* for chaining.
    """
    now = time.time()
    runs = [
        {
            "id": "20260101_120000_aaaaaa",
            "path": "train/cifar10",
            "status": "finished",
            "metrics": [("loss", 0.5, 1), ("loss", 0.3, 2)],
        },
        {
            "id": "20260102_120000_bbbbbb",
            "path": "train/cifar10",
            "status": "running",
            "metrics": [("loss", 0.8, 1)],
        },
        {
            "id": "20260103_120000_cccccc",
            "path": "eval/imagenet",
            "status": "failed",
            "metrics": [],
        },
    ]

    for i, r in enumerate(runs):
        run_dir = storage_root / "runs" / r["path"] / r["id"]
        run_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "id": r["id"],
            "path": r["path"],
            "created_at": now - (len(runs) - i) * 3600,
            "pid": None,
            "hostname": "testhost",
        }
        (run_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8"
        )

        status = {
            "status": r["status"],
            "started_at": now - (len(runs) - i) * 3600,
        }
        if r["status"] == "finished":
            status["ended_at"] = now - (len(runs) - i) * 1800
        (run_dir / "status.json").write_text(
            json.dumps(status, ensure_ascii=False), encoding="utf-8"
        )

        if r["metrics"]:
            lines = []
            for name, value, step in r["metrics"]:
                lines.append(json.dumps({
                    "timestamp": now,
                    "metrics": {name: value},
                    "step": step,
                }))
            (run_dir / "events.jsonl").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )

    return storage_root


@pytest.fixture
def populated_db(sqlite_backend, populated_storage: Path):
    """Sync the pre-populated file-system runs into SQLite.

    Returns the *sqlite_backend* with data loaded.
    """
    from runicorn.storage.models import ExperimentRecord, MetricRecord
    from runicorn.storage.file_utils import iter_all_runs, read_json

    for entry in iter_all_runs(populated_storage):
        meta = read_json(entry.dir / "meta.json")
        status = read_json(entry.dir / "status.json")

        record = ExperimentRecord(
            id=meta["id"],
            path=meta.get("path", "default"),
            created_at=meta.get("created_at", time.time()),
            updated_at=time.time(),
            status=status.get("status", "running"),
            started_at=status.get("started_at"),
            ended_at=status.get("ended_at"),
            run_dir=str(entry.dir),
            pid=meta.get("pid"),
            hostname=meta.get("hostname"),
        )
        sqlite_backend.create_experiment(record)

        events_path = entry.dir / "events.jsonl"
        if events_path.exists():
            metrics = []
            for line in events_path.read_text(encoding="utf-8").strip().splitlines():
                evt = json.loads(line)
                for name, value in evt.get("metrics", {}).items():
                    metrics.append(MetricRecord(
                        experiment_id=meta["id"],
                        timestamp=evt["timestamp"],
                        metric_name=name,
                        metric_value=value,
                        step=evt.get("step"),
                    ))
            if metrics:
                sqlite_backend.log_metrics(meta["id"], metrics)

    return sqlite_backend
