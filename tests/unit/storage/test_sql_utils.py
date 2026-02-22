"""Tests for runicorn.storage.sql_utils — column name validation."""
from __future__ import annotations

import pytest

from runicorn.storage.sql_utils import (
    validate_column_name,
    safe_column_list,
    ALLOWED_EXPERIMENT_COLUMNS,
)


class TestValidateColumnName:

    def test_valid_column(self) -> None:
        assert validate_column_name("status", ALLOWED_EXPERIMENT_COLUMNS) is True

    def test_invalid_not_in_whitelist(self) -> None:
        assert validate_column_name("id", ALLOWED_EXPERIMENT_COLUMNS) is False

    def test_sql_injection_rejected(self) -> None:
        assert validate_column_name("status; DROP TABLE", ALLOWED_EXPERIMENT_COLUMNS) is False

    def test_sql_keyword_rejected(self) -> None:
        assert validate_column_name("SELECT") is False
        assert validate_column_name("DROP") is False

    def test_no_whitelist_pattern_only(self) -> None:
        assert validate_column_name("my_col") is True
        assert validate_column_name("123bad") is False


class TestSafeColumnList:

    def test_valid_list(self) -> None:
        result = safe_column_list(["status", "alias"], ALLOWED_EXPERIMENT_COLUMNS)
        assert result == ["status", "alias"]

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid column name"):
            safe_column_list(["status", "DROP"], ALLOWED_EXPERIMENT_COLUMNS)
