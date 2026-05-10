from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from ..backends import SQLiteStorageBackend


def set_tags(backend: "SQLiteStorageBackend", exp_id: str, tags: List[str]) -> None:
    conn = backend.pool.get_connection()
    try:
        conn.execute("DELETE FROM experiment_tags WHERE experiment_id = ?", (exp_id,))
        if tags:
            conn.executemany(
                "INSERT OR IGNORE INTO experiment_tags (experiment_id, tag) VALUES (?, ?)",
                [(exp_id, tag) for tag in tags],
            )
        conn.commit()
    finally:
        backend.pool.return_connection(conn)


def get_tags(backend: "SQLiteStorageBackend", exp_id: str) -> List[str]:
    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(
            "SELECT tag FROM experiment_tags WHERE experiment_id = ? ORDER BY tag",
            (exp_id,),
        ).fetchall()
        return [row["tag"] for row in rows]
    finally:
        backend.pool.return_connection(conn)


def list_experiments_for_viewer(
    backend: "SQLiteStorageBackend", *, include_deleted: bool = False
 ) -> List[Dict[str, object]]:
    sql = """
        SELECT e.*,
               GROUP_CONCAT(DISTINCT t.tag) AS tags_csv,
               COUNT(DISTINCT ra.asset_id)  AS assets_count
        FROM experiments e
        LEFT JOIN experiment_tags t  ON e.id = t.experiment_id
        LEFT JOIN run_assets      ra ON e.id = ra.run_id
    """
    if not include_deleted:
        sql += " WHERE e.deleted_at IS NULL"
    sql += " GROUP BY e.id ORDER BY e.created_at DESC"

    conn = backend.pool.get_connection()
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        backend.pool.return_connection(conn)


def list_deleted_for_viewer(backend: "SQLiteStorageBackend") -> List[Dict[str, object]]:
    sql = """
        SELECT id, path, alias, created_at, status,
               deleted_at, delete_reason, run_dir
        FROM experiments
        WHERE deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """
    conn = backend.pool.get_connection()
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        backend.pool.return_connection(conn)


def get_unique_paths(backend: "SQLiteStorageBackend") -> List[str]:
    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT path FROM experiments WHERE deleted_at IS NULL ORDER BY path"
        ).fetchall()
        return [r["path"] for r in rows]
    finally:
        backend.pool.return_connection(conn)


def get_path_stats(backend: "SQLiteStorageBackend") -> Dict[str, Dict[str, int]]:
    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT path,
                   COUNT(*)                                      AS total,
                   COUNT(CASE WHEN status='running'  THEN 1 END) AS running,
                   COUNT(CASE WHEN status='finished' THEN 1 END) AS finished,
                   COUNT(CASE WHEN status='failed'   THEN 1 END) AS failed
            FROM experiments
            WHERE deleted_at IS NULL
            GROUP BY path
            """
        ).fetchall()
    finally:
        backend.pool.return_connection(conn)

    path_runs: Dict[str, Dict[str, int]] = {}
    for r in rows:
        path_runs[r["path"]] = {
            "total": r["total"],
            "running": r["running"],
            "finished": r["finished"],
            "failed": r["failed"],
        }

    for path in list(path_runs.keys()):
        parts = path.split("/")
        for i in range(1, len(parts)):
            ancestor = "/".join(parts[:i])
            if ancestor not in path_runs:
                path_runs[ancestor] = {"total": 0, "running": 0, "finished": 0, "failed": 0}
            for key in ("total", "running", "finished", "failed"):
                path_runs[ancestor][key] += path_runs[path][key]

    return path_runs


def get_running_experiments(backend: "SQLiteStorageBackend") -> List[Dict[str, object]]:
    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(
            "SELECT id, run_dir, pid FROM experiments WHERE status = 'running' AND deleted_at IS NULL"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        backend.pool.return_connection(conn)


def experiment_exists(backend: "SQLiteStorageBackend", exp_id: str) -> bool:
    conn = backend.pool.get_connection()
    try:
        row = conn.execute("SELECT 1 FROM experiments WHERE id = ?", (exp_id,)).fetchone()
        return row is not None
    finally:
        backend.pool.return_connection(conn)
