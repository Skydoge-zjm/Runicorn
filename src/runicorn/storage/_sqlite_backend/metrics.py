from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, List, Optional

from ..models import MetricRecord, StorageStats

if TYPE_CHECKING:
    from ..backends import SQLiteStorageBackend

logger = logging.getLogger(__name__)


def log_metrics(backend: "SQLiteStorageBackend", exp_id: str, metrics: List[MetricRecord]) -> bool:
    if not metrics:
        return True

    conn = backend.pool.get_connection()
    try:
        metric_data = [
            (m.experiment_id, m.timestamp, m.metric_name, m.metric_value, m.step, m.stage, m.recorded_at)
            for m in metrics
        ]
        conn.executemany(
            """
            INSERT INTO metrics
            (experiment_id, timestamp, metric_name, metric_value, step, stage, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            metric_data,
        )
        conn.execute(
            """
            UPDATE experiments
            SET metric_count = (
                SELECT COUNT(*) FROM metrics WHERE experiment_id = ?
            ), updated_at = ?
            WHERE id = ?
            """,
            (exp_id, time.time(), exp_id),
        )
        conn.commit()
        logger.debug(f"Logged {len(metrics)} metrics for experiment {exp_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to log metrics for {exp_id}: {e}")
        return False
    finally:
        backend.pool.return_connection(conn)


def get_metrics(
    backend: "SQLiteStorageBackend", exp_id: str, metric_names: Optional[List[str]] = None
) -> List[MetricRecord]:
    sql = """
        SELECT experiment_id, timestamp, metric_name, metric_value, step, stage, recorded_at
        FROM metrics
        WHERE experiment_id = ?
    """
    params: list[object] = [exp_id]
    if metric_names:
        placeholders = ",".join("?" * len(metric_names))
        sql += f" AND metric_name IN ({placeholders})"
        params.extend(metric_names)
    sql += " ORDER BY timestamp ASC, id ASC"

    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [MetricRecord.from_dict(dict(row)) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get metrics for {exp_id}: {e}")
        return []
    finally:
        backend.pool.return_connection(conn)


def get_storage_stats(backend: "SQLiteStorageBackend") -> StorageStats:
    conn = backend.pool.get_connection()
    try:
        exp_counts = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active,
                COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted
            FROM experiments
            """
        ).fetchone()
        metric_count = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        db_size_bytes = page_count * page_size
        return StorageStats(
            total_experiments=exp_counts[0],
            active_experiments=exp_counts[1],
            deleted_experiments=exp_counts[2],
            total_metrics_points=metric_count,
            storage_size_bytes=db_size_bytes,
            db_size_mb=db_size_bytes / (1024 * 1024),
            updated_at=time.time(),
        )
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        return StorageStats()
    finally:
        backend.pool.return_connection(conn)

