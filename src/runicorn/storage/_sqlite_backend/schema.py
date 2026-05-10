from __future__ import annotations

import logging
import sqlite3
from importlib.resources import files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backends import SQLiteStorageBackend

logger = logging.getLogger(__name__)


def initialize_schema(backend: "SQLiteStorageBackend") -> None:
    backend._migrate_legacy_schema()
    backend._migrate_metrics_identity_schema()

    try:
        schema_sql = files("runicorn.storage").joinpath("schema.sql").read_text(encoding="utf-8")
        conn = backend.pool.get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database schema initialized successfully")
        finally:
            backend.pool.return_connection(conn)
    except FileNotFoundError:
        logger.error(
            "Failed to initialize database schema: missing packaged resource schema.sql. "
            "This usually means the installed wheel/sdist is incomplete."
        )
        raise
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def migrate_legacy_schema(backend: "SQLiteStorageBackend") -> None:
    conn = backend.pool.get_connection()
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'"
        )
        if not cursor.fetchone():
            return

        cursor = conn.execute("PRAGMA table_info(experiments)")
        columns = {row[1] for row in cursor}
        if "project" not in columns:
            return

        needs_add_columns = "path" not in columns
        logger.info("Detected legacy schema (project/name), migrating to new schema (path/alias/workspace_root)...")

        if needs_add_columns:
            for col_sql in [
                "ALTER TABLE experiments ADD COLUMN path TEXT NOT NULL DEFAULT 'default'",
                "ALTER TABLE experiments ADD COLUMN alias TEXT",
                "ALTER TABLE experiments ADD COLUMN workspace_root TEXT",
            ]:
                try:
                    conn.execute(col_sql)
                except sqlite3.OperationalError:
                    pass

            conn.execute(
                """
                UPDATE experiments
                SET path = CASE
                    WHEN name IS NOT NULL AND name != '' THEN project || '/' || name
                    ELSE project
                END
                WHERE path = 'default'
                """
            )

        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
        for row in cursor.fetchall():
            conn.execute(f"DROP VIEW IF EXISTS {row[0]}")

        cursor = conn.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND tbl_name='experiments' AND sql IS NOT NULL"
        )
        for row in cursor.fetchall():
            if "project" in row[1] or '"name"' in row[1] or ", name" in row[1] or "(name" in row[1]:
                conn.execute(f"DROP INDEX IF EXISTS {row[0]}")

        for col in ("project", "name"):
            try:
                conn.execute(f"ALTER TABLE experiments DROP COLUMN {col}")
            except sqlite3.OperationalError as e:
                logger.debug(f"Could not drop column {col}: {e}")

        conn.commit()
        logger.info("Legacy schema migration completed")
    except Exception as e:
        logger.warning(f"Legacy schema migration failed: {e}")
    finally:
        backend.pool.return_connection(conn)


def migrate_metrics_identity_schema(backend: "SQLiteStorageBackend") -> None:
    conn = backend.pool.get_connection()
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'"
        )
        if not cursor.fetchone():
            return

        cursor = conn.execute("PRAGMA table_info(metrics)")
        columns = {row[1] for row in cursor.fetchall()}
        if "id" in columns:
            return

        logger.info("Detected legacy metrics schema without stable row identity; migrating...")

        conn.execute("DROP TABLE IF EXISTS metrics__new")
        conn.execute(
            """
            CREATE TABLE metrics__new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                step INTEGER,
                stage TEXT,
                recorded_at REAL NOT NULL DEFAULT (unixepoch()),
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            INSERT INTO metrics__new (
                experiment_id,
                timestamp,
                metric_name,
                metric_value,
                step,
                stage,
                recorded_at
            )
            SELECT
                experiment_id,
                timestamp,
                metric_name,
                metric_value,
                step,
                stage,
                COALESCE(recorded_at, timestamp, unixepoch())
            FROM metrics
            ORDER BY timestamp ASC
            """
        )
        conn.execute("DROP TABLE metrics")
        conn.execute("ALTER TABLE metrics__new RENAME TO metrics")
        conn.commit()
        logger.info("Legacy metrics schema migration completed")
    except Exception as e:
        conn.rollback()
        logger.error(f"Metrics schema migration failed: {e}")
        raise
    finally:
        backend.pool.return_connection(conn)

