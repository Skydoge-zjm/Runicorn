from __future__ import annotations

import json
import sqlite3
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..backends import SQLiteStorageBackend


def upsert_asset(
    backend: "SQLiteStorageBackend",
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
    conn = backend.pool.get_connection()
    try:
        asset_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False) if metadata is not None else None
        try:
            conn.execute(
                """
                INSERT INTO assets (
                    asset_id, asset_type, name, source_uri, archive_uri,
                    is_archived, fingerprint_kind, fingerprint,
                    size_bytes, mtime, created_at, metadata_json
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
    finally:
        backend.pool.return_connection(conn)


def link_run_asset(
    backend: "SQLiteStorageBackend",
    *,
    run_id: str,
    asset_id: str,
    role: str,
    created_at: Optional[float] = None,
) -> None:
    conn = backend.pool.get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO run_assets (run_id, asset_id, role, created_at) VALUES (?, ?, ?, ?)",
            (run_id, asset_id, role, created_at),
        )
        conn.commit()
    finally:
        backend.pool.return_connection(conn)


def record_asset_for_run(backend: "SQLiteStorageBackend", **kwargs) -> str:
    asset_id = upsert_asset(
        backend,
        asset_type=kwargs["asset_type"],
        name=kwargs["name"],
        source_uri=kwargs["source_uri"],
        archive_uri=kwargs["archive_uri"],
        is_archived=kwargs["is_archived"],
        fingerprint_kind=kwargs["fingerprint_kind"],
        fingerprint=kwargs["fingerprint"],
        size_bytes=kwargs.get("size_bytes"),
        mtime=kwargs.get("mtime"),
        created_at=kwargs.get("created_at"),
        metadata=kwargs.get("metadata"),
    )
    link_run_asset(
        backend,
        run_id=kwargs["run_id"],
        asset_id=asset_id,
        role=kwargs["role"],
        created_at=kwargs.get("created_at"),
    )
    return asset_id


def get_assets_for_run(backend: "SQLiteStorageBackend", run_id: str) -> List[Dict[str, Any]]:
    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT a.*, ra.role, ra.created_at AS linked_at
            FROM assets a
            JOIN run_assets ra ON a.asset_id = ra.asset_id
            WHERE ra.run_id = ?
            """,
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        backend.pool.return_connection(conn)


def get_asset_ref_count(backend: "SQLiteStorageBackend", asset_id: str) -> int:
    conn = backend.pool.get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM run_assets WHERE asset_id = ?", (asset_id,)).fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        backend.pool.return_connection(conn)


def count_runs_referencing_fingerprint(
    backend: "SQLiteStorageBackend", fingerprint: str, exclude_run_id: Optional[str] = None
) -> int:
    if not fingerprint:
        return 0
    conn = backend.pool.get_connection()
    try:
        if exclude_run_id:
            row = conn.execute(
                """
                SELECT COUNT(DISTINCT ra.run_id) AS cnt
                FROM run_assets ra
                JOIN assets a ON ra.asset_id = a.asset_id
                WHERE a.fingerprint = ? AND ra.run_id != ?
                """,
                (fingerprint, exclude_run_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT COUNT(DISTINCT ra.run_id) AS cnt
                FROM run_assets ra
                JOIN assets a ON ra.asset_id = a.asset_id
                WHERE a.fingerprint = ?
                """,
                (fingerprint,),
            ).fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        backend.pool.return_connection(conn)


def unlink_run_asset(backend: "SQLiteStorageBackend", run_id: str, asset_id: str) -> None:
    conn = backend.pool.get_connection()
    try:
        conn.execute("DELETE FROM run_assets WHERE run_id = ? AND asset_id = ?", (run_id, asset_id))
        conn.commit()
    finally:
        backend.pool.return_connection(conn)


def get_asset_by_fingerprint(
    backend: "SQLiteStorageBackend", asset_type: str, fingerprint: str
) -> Optional[Dict[str, Any]]:
    conn = backend.pool.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM assets WHERE asset_type=? AND fingerprint=?",
            (asset_type, fingerprint),
        ).fetchone()
        return dict(row) if row else None
    finally:
        backend.pool.return_connection(conn)


def delete_run_with_orphan_assets(backend: "SQLiteStorageBackend", run_id: str) -> Dict[str, Any]:
    conn = backend.pool.get_connection()
    try:
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
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM run_assets WHERE asset_id=? AND run_id!=?",
                (asset_id, run_id),
            ).fetchone()
            ref_count = int(row["cnt"]) if row else 0
            asset_dict = dict(asset)
            if ref_count == 0:
                orphaned.append(asset_dict)
            else:
                kept.append(asset_dict)

        conn.execute("DELETE FROM experiments WHERE id=?", (run_id,))
        for asset in orphaned:
            conn.execute("DELETE FROM assets WHERE asset_id=?", (asset["asset_id"],))
        conn.commit()
        return {"orphaned_assets": orphaned, "kept_assets": kept}
    finally:
        backend.pool.return_connection(conn)

