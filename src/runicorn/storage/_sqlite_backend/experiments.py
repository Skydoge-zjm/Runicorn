from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..models import ExperimentRecord, QueryParams
from ..sql_utils import ALLOWED_EXPERIMENT_COLUMNS, validate_column_name

if TYPE_CHECKING:
    from ..backends import SQLiteStorageBackend

logger = logging.getLogger(__name__)


def create_experiment(backend: "SQLiteStorageBackend", experiment: ExperimentRecord) -> str:
    conn = backend.pool.get_connection()
    try:
        conn.execute(
            """
            INSERT INTO experiments (
                id, path, alias, created_at, updated_at, status,
                pid, python_version, platform, hostname, run_dir,
                workspace_root,
                best_metric_name, best_metric_value, best_metric_step, best_metric_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment.id,
                experiment.path,
                experiment.alias,
                experiment.created_at,
                experiment.updated_at,
                experiment.status,
                experiment.pid,
                experiment.python_version,
                experiment.platform,
                experiment.hostname,
                experiment.run_dir,
                experiment.workspace_root,
                experiment.best_metric_name,
                experiment.best_metric_value,
                experiment.best_metric_step,
                experiment.best_metric_mode,
            ),
        )
        conn.commit()
        logger.debug(f"Created experiment {experiment.id} in database")
        return experiment.id
    except Exception as e:
        logger.error(f"Failed to create experiment {experiment.id}: {e}")
        raise
    finally:
        backend.pool.return_connection(conn)


def update_experiment(backend: "SQLiteStorageBackend", exp_id: str, updates: Dict[str, Any]) -> bool:
    if not updates:
        return True

    set_clauses = []
    params = []
    for key, value in updates.items():
        if not validate_column_name(key, ALLOWED_EXPERIMENT_COLUMNS):
            logger.warning(f"Rejecting invalid column name in update: {key}")
            continue
        set_clauses.append(f"{key} = ?")
        params.append(value)

    if not set_clauses:
        logger.warning("No valid columns to update")
        return False

    set_clauses.append("updated_at = ?")
    params.append(time.time())
    params.append(exp_id)
    query = f"UPDATE experiments SET {', '.join(set_clauses)} WHERE id = ?"

    conn = backend.pool.get_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.debug(f"Updated experiment {exp_id} with {len(updates)} fields")
        else:
            logger.warning(f"No experiment found with ID {exp_id}")
        return success
    except Exception as e:
        logger.error(f"Failed to update experiment {exp_id}: {e}")
        return False
    finally:
        backend.pool.return_connection(conn)


def get_experiment(backend: "SQLiteStorageBackend", exp_id: str) -> Optional[ExperimentRecord]:
    conn = backend.pool.get_connection()
    try:
        row = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
        return ExperimentRecord.from_dict(dict(row)) if row else None
    except Exception as e:
        logger.error(f"Failed to get experiment {exp_id}: {e}")
        return None
    finally:
        backend.pool.return_connection(conn)


def _build_experiment_filters(query: QueryParams) -> tuple[list[str], list[Any]]:
    where_clauses: list[str] = []
    params: list[Any] = []

    if not query.include_deleted:
        where_clauses.append("deleted_at IS NULL")
    if query.path:
        if query.path_exact:
            where_clauses.append("path = ?")
            params.append(query.path)
        else:
            where_clauses.append("(path = ? OR path LIKE ?)")
            params.append(query.path)
            params.append(f"{query.path}/%")
    if query.alias:
        where_clauses.append("alias LIKE ?")
        params.append(f"%{query.alias}%")
    if query.status:
        placeholders = ",".join("?" * len(query.status))
        where_clauses.append(f"status IN ({placeholders})")
        params.extend(query.status)
    if query.created_after:
        where_clauses.append("created_at >= ?")
        params.append(query.created_after)
    if query.created_before:
        where_clauses.append("created_at <= ?")
        params.append(query.created_before)
    if query.search_text:
        where_clauses.append("(path LIKE ? OR alias LIKE ? OR id LIKE ?)")
        search_pattern = f"%{query.search_text}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    if query.best_metric_range:
        where_clauses.append("best_metric_value BETWEEN ? AND ?")
        params.extend(query.best_metric_range)

    return where_clauses, params


def list_experiments(backend: "SQLiteStorageBackend", query: QueryParams) -> List[ExperimentRecord]:
    sql_parts = ["SELECT * FROM experiments"]
    where_clauses, params = _build_experiment_filters(query)
    if where_clauses:
        sql_parts.append("WHERE " + " AND ".join(where_clauses))

    order_direction = "DESC" if query.order_desc else "ASC"
    sql_parts.append(f"ORDER BY {query.order_by} {order_direction}")
    sql_parts.append("LIMIT ? OFFSET ?")
    params.extend([query.limit, query.offset])

    conn = backend.pool.get_connection()
    try:
        rows = conn.execute(" ".join(sql_parts), params).fetchall()
        return [ExperimentRecord.from_dict(dict(row)) for row in rows]
    except Exception as e:
        logger.error(f"Failed to list experiments: {e}")
        return []
    finally:
        backend.pool.return_connection(conn)


def count_experiments(backend: "SQLiteStorageBackend", query: QueryParams) -> int:
    sql_parts = ["SELECT COUNT(*) FROM experiments"]
    where_clauses, params = _build_experiment_filters(query)
    if where_clauses:
        sql_parts.append("WHERE " + " AND ".join(where_clauses))

    conn = backend.pool.get_connection()
    try:
        return int(conn.execute(" ".join(sql_parts), params).fetchone()[0])
    except Exception as e:
        logger.error(f"Failed to count experiments: {e}")
        return 0
    finally:
        backend.pool.return_connection(conn)


def soft_delete_experiments(
    backend: "SQLiteStorageBackend", exp_ids: List[str], reason: str = "user_deleted"
) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    conn = backend.pool.get_connection()
    try:
        for exp_id in exp_ids:
            cursor = conn.execute(
                """
                UPDATE experiments
                SET deleted_at = ?, delete_reason = ?, updated_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (time.time(), reason, time.time(), exp_id),
            )
            results[exp_id] = cursor.rowcount > 0
            if results[exp_id]:
                logger.info(f"Soft deleted experiment {exp_id}")
            else:
                logger.warning(f"Experiment {exp_id} not found or already deleted")
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to soft delete experiments: {e}")
        for exp_id in exp_ids:
            results[exp_id] = False
    finally:
        backend.pool.return_connection(conn)

    return results


def restore_experiments(backend: "SQLiteStorageBackend", exp_ids: List[str]) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    conn = backend.pool.get_connection()
    try:
        for exp_id in exp_ids:
            cursor = conn.execute(
                """
                UPDATE experiments
                SET deleted_at = NULL, delete_reason = NULL, updated_at = ?
                WHERE id = ? AND deleted_at IS NOT NULL
                """,
                (time.time(), exp_id),
            )
            results[exp_id] = cursor.rowcount > 0
            if results[exp_id]:
                logger.info(f"Restored experiment {exp_id}")
            else:
                logger.warning(f"Experiment {exp_id} not found or not deleted")
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to restore experiments: {e}")
        for exp_id in exp_ids:
            results[exp_id] = False
    finally:
        backend.pool.return_connection(conn)

    return results

