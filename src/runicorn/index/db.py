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

    # -------------------- Query Methods --------------------

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run info by run_id."""
        conn = self._connect()
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row:
            return dict(row)
        return None

    def get_assets_for_run(self, run_id: str) -> list[Dict[str, Any]]:
        """
        Get all assets associated with a run.
        
        Returns:
            List of asset records with role info.
        """
        conn = self._connect()
        rows = conn.execute(
            """
SELECT a.*, ra.role, ra.created_at as linked_at
FROM assets a
JOIN run_assets ra ON a.asset_id = ra.asset_id
WHERE ra.run_id = ?
""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_runs_for_asset(self, asset_id: str) -> list[str]:
        """
        Get all run_ids that reference an asset.
        
        Returns:
            List of run_ids.
        """
        conn = self._connect()
        rows = conn.execute(
            "SELECT run_id FROM run_assets WHERE asset_id = ?",
            (asset_id,),
        ).fetchall()
        return [r["run_id"] for r in rows]

    def get_asset_ref_count(self, asset_id: str) -> int:
        """
        Get the number of runs referencing an asset.
        
        Returns:
            Reference count.
        """
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM run_assets WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()
        return int(row["cnt"]) if row else 0

    def get_asset_by_fingerprint(self, asset_type: str, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Get asset by type and fingerprint."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM assets WHERE asset_type=? AND fingerprint=?",
            (asset_type, fingerprint),
        ).fetchone()
        if row:
            return dict(row)
        return None

    # -------------------- Delete Methods --------------------

    def unlink_run_asset(self, run_id: str, asset_id: str) -> None:
        """Remove the link between a run and an asset."""
        with self._lock:
            conn = self._connect()
            conn.execute(
                "DELETE FROM run_assets WHERE run_id=? AND asset_id=?",
                (run_id, asset_id),
            )
            conn.commit()

    def delete_asset(self, asset_id: str) -> None:
        """Delete an asset record (does not delete files)."""
        with self._lock:
            conn = self._connect()
            # CASCADE will delete run_assets links
            conn.execute("DELETE FROM assets WHERE asset_id=?", (asset_id,))
            conn.commit()

    def delete_run(self, run_id: str) -> None:
        """Delete a run record (does not delete files)."""
        with self._lock:
            conn = self._connect()
            # CASCADE will delete run_assets links
            conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
            conn.commit()

    def delete_run_with_orphan_assets(self, run_id: str) -> Dict[str, Any]:
        """
        Delete a run and any assets that become orphaned (no other runs reference them).
        
        This method:
        1. Finds all assets linked to the run
        2. For each asset, checks if other runs reference it
        3. If no other runs reference it, marks it for deletion
        4. Deletes the run record (CASCADE deletes run_assets links)
        5. Deletes orphaned asset records
        
        Returns:
            Dict with:
            - orphaned_assets: list of asset records that were orphaned
            - kept_assets: list of asset records still referenced by other runs
        
        Note: This does NOT delete actual files. Caller must handle file deletion.
        """
        with self._lock:
            conn = self._connect()
            
            # Get all assets for this run
            assets = conn.execute(
                """
SELECT a.*, ra.role
FROM assets a
JOIN run_assets ra ON a.asset_id = ra.asset_id
WHERE ra.run_id = ?
""",
                (run_id,),
            ).fetchall()
            
            orphaned = []
            kept = []
            
            for asset in assets:
                asset_id = asset["asset_id"]
                # Count references excluding current run
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM run_assets WHERE asset_id=? AND run_id!=?",
                    (asset_id, run_id),
                ).fetchone()
                ref_count = int(row["cnt"]) if row else 0
                
                asset_dict = dict(asset)
                if ref_count == 0:
                    orphaned.append(asset_dict)
                else:
                    kept.append(asset_dict)
            
            # Delete run (CASCADE deletes run_assets)
            conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
            
            # Delete orphaned assets
            for asset in orphaned:
                conn.execute("DELETE FROM assets WHERE asset_id=?", (asset["asset_id"],))
            
            conn.commit()
            
            return {
                "orphaned_assets": orphaned,
                "kept_assets": kept,
            }
