from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from filelock import FileLock


class IndexDb:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = Path(storage_root)
        self.db_path = self.storage_root / "index" / "runicorn.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.db_path) + ".lock")
        self._local = threading.local()
        self._conns_lock = threading.Lock()
        self._conns: Dict[int, sqlite3.Connection] = {}

        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        self._local.conn = conn
        with self._conns_lock:
            self._conns[id(conn)] = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            return
        try:
            conn.close()
        finally:
            self._local.conn = None
            with self._conns_lock:
                self._conns.pop(id(conn), None)

    def close_all(self) -> None:
        with self._conns_lock:
            conns = list(self._conns.values())
            self._conns.clear()
        for c in conns:
            try:
                c.close()
            except Exception:
                pass
        self._local.conn = None

    def _ensure_schema(self) -> None:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA busy_timeout=5000;")
                conn.execute("PRAGMA foreign_keys=ON;")

                conn.executescript(
                    """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  project TEXT NULL,
  name TEXT NULL,
  created_at REAL NULL,
  ended_at REAL NULL,
  status TEXT NULL,
  run_dir TEXT NOT NULL,
  workspace_root TEXT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  asset_type TEXT NOT NULL,
  name TEXT NULL,
  source_uri TEXT NULL,
  archive_uri TEXT NULL,
  is_archived INTEGER NOT NULL,
  fingerprint_kind TEXT NULL,
  fingerprint TEXT NULL,
  size_bytes INTEGER NULL,
  mtime REAL NULL,
  created_at REAL NULL,
  metadata_json TEXT NULL
);

CREATE TABLE IF NOT EXISTS run_assets (
  run_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at REAL NULL,
  PRIMARY KEY (run_id, asset_id, role),
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
  FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assets_type_name ON assets(asset_type, name);
CREATE INDEX IF NOT EXISTS idx_assets_fingerprint ON assets(fingerprint);
CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_type_fingerprint_unique ON assets(asset_type, fingerprint);
CREATE INDEX IF NOT EXISTS idx_run_assets_run ON run_assets(run_id);
CREATE INDEX IF NOT EXISTS idx_run_assets_asset ON run_assets(asset_id);
"""
                )
                conn.commit()
            finally:
                conn.close()

    def upsert_run(
        self,
        *,
        run_id: str,
        project: str,
        name: Optional[str],
        created_at: float,
        status: str,
        run_dir: str,
        workspace_root: Optional[str],
    ) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                """
INSERT INTO runs(run_id, project, name, created_at, status, run_dir, workspace_root)
VALUES(?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(run_id) DO UPDATE SET
  project=excluded.project,
  name=excluded.name,
  created_at=excluded.created_at,
  status=excluded.status,
  run_dir=excluded.run_dir,
  workspace_root=excluded.workspace_root
""",
                (run_id, project, name, float(created_at), status, run_dir, workspace_root),
            )
            conn.commit()

    def finish_run(self, *, run_id: str, status: str, ended_at: float) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                "UPDATE runs SET status=?, ended_at=? WHERE run_id=?",
                (status, float(ended_at), run_id),
            )
            conn.commit()

    def upsert_asset(
        self,
        *,
        asset_type: str,
        name: Optional[str],
        source_uri: Optional[str],
        archive_uri: Optional[str],
        is_archived: bool,
        fingerprint_kind: Optional[str],
        fingerprint: Optional[str],
        size_bytes: Optional[int] = None,
        mtime: Optional[float] = None,
        created_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        with self._lock:
            conn = self._connect()

            asset_id = str(uuid.uuid4())
            metadata_json = json.dumps(metadata or {}, ensure_ascii=False) if metadata is not None else None

            try:
                conn.execute(
                    """
INSERT INTO assets(
  asset_id, asset_type, name, source_uri, archive_uri, is_archived,
  fingerprint_kind, fingerprint, size_bytes, mtime, created_at, metadata_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""",
                    (
                        asset_id,
                        asset_type,
                        name,
                        source_uri,
                        archive_uri,
                        1 if is_archived else 0,
                        fingerprint_kind,
                        fingerprint,
                        size_bytes,
                        mtime,
                        created_at,
                        metadata_json,
                    ),
                )
                conn.commit()
                return asset_id
            except sqlite3.IntegrityError:
                if fingerprint:
                    row = conn.execute(
                        "SELECT asset_id FROM assets WHERE asset_type=? AND fingerprint=?",
                        (asset_type, fingerprint),
                    ).fetchone()
                    if row:
                        return str(row["asset_id"])
                raise

    def link_run_asset(self, *, run_id: str, asset_id: str, role: str, created_at: Optional[float] = None) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT OR IGNORE INTO run_assets(run_id, asset_id, role, created_at) VALUES(?, ?, ?, ?)",
                (run_id, asset_id, role, created_at),
            )
            conn.commit()

    def record_asset_for_run(
        self,
        *,
        run_id: str,
        role: str,
        asset_type: str,
        name: Optional[str],
        source_uri: Optional[str],
        archive_uri: Optional[str],
        is_archived: bool,
        fingerprint_kind: Optional[str],
        fingerprint: Optional[str],
        size_bytes: Optional[int] = None,
        mtime: Optional[float] = None,
        created_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        asset_id = self.upsert_asset(
            asset_type=asset_type,
            name=name,
            source_uri=source_uri,
            archive_uri=archive_uri,
            is_archived=is_archived,
            fingerprint_kind=fingerprint_kind,
            fingerprint=fingerprint,
            size_bytes=size_bytes,
            mtime=mtime,
            created_at=created_at,
            metadata=metadata,
        )
        self.link_run_asset(run_id=run_id, asset_id=asset_id, role=role, created_at=created_at)
        return asset_id
