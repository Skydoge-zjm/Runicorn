"""Tests for runicorn.storage.backends.ConnectionPool."""
from __future__ import annotations

import queue
import sqlite3
from pathlib import Path

import pytest

from runicorn.storage.backends import ConnectionPool


class TestConnectionPool:

    def test_init_creates_pool_size_connections(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        pool = ConnectionPool(db, pool_size=3)

        assert pool.pool.qsize() == 3
        assert len(pool.all_connections) == 3
        pool.close_all()

    def test_get_and_return_connection(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        pool = ConnectionPool(db, pool_size=2)

        conn = pool.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert pool.pool.qsize() == 1  # one taken out

        pool.return_connection(conn)
        assert pool.pool.qsize() == 2
        pool.close_all()

    def test_close_all_empties_pool(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        pool = ConnectionPool(db, pool_size=3)

        pool.close_all()

        assert pool.pool.empty()
        assert len(pool.all_connections) == 0

    def test_connections_have_row_factory(self, tmp_path: Path) -> None:
        """Connections must use sqlite3.Row for dict-like access."""
        db = tmp_path / "test.db"
        pool = ConnectionPool(db, pool_size=1)

        conn = pool.get_connection()
        assert conn.row_factory is sqlite3.Row
        pool.return_connection(conn)
        pool.close_all()
