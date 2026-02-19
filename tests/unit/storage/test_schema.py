"""Tests for storage/schema.sql — DDL completeness and idempotency."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


EXPECTED_TABLES = {
    "experiments",
    "metrics",
    "experiment_tags",
    "environments",
    "experiment_files",
    "query_cache",
    "assets",
    "run_assets",
    "storage_stats",
}

EXPECTED_VIEWS = {
    "v_path_stats",
    "v_best_experiments",
    "v_recent_activity",
}


@pytest.fixture
def db_conn(tmp_path: Path):
    """Create an in-memory-like SQLite DB with schema applied."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))

    schema_sql = (
        Path(__file__).resolve().parents[3]
        / "src" / "runicorn" / "storage" / "schema.sql"
    ).read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()
    yield conn
    conn.close()


class TestSchema:

    def test_creates_all_tables(self, db_conn: sqlite3.Connection) -> None:
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {r[0] for r in rows}

        assert EXPECTED_TABLES.issubset(table_names), (
            f"Missing tables: {EXPECTED_TABLES - table_names}"
        )

    def test_creates_views(self, db_conn: sqlite3.Connection) -> None:
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()
        view_names = {r[0] for r in rows}

        assert EXPECTED_VIEWS.issubset(view_names), (
            f"Missing views: {EXPECTED_VIEWS - view_names}"
        )

    def test_wal_mode(self, db_conn: sqlite3.Connection) -> None:
        mode = db_conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_idempotent(self, db_conn: sqlite3.Connection) -> None:
        """Executing schema.sql twice should not raise."""
        schema_sql = (
            Path(__file__).resolve().parents[3]
            / "src" / "runicorn" / "storage" / "schema.sql"
        ).read_text(encoding="utf-8")

        db_conn.executescript(schema_sql)  # second execution
        db_conn.commit()

        # Still has all tables
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert len(rows) >= len(EXPECTED_TABLES)
