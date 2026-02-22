"""Tests for runicorn.config.user_config — config.json read/write."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runicorn.config.user_config import (
    load_user_config,
    save_user_config,
    get_user_root_dir,
    set_user_root_dir,
)


class TestLoadUserConfig:

    def test_load_empty_config(self, mock_config_root: Path) -> None:
        """No config.json on disk → return empty dict."""
        assert load_user_config() == {}

    def test_load_existing_config(self, mock_config_root: Path) -> None:
        cfg_path = mock_config_root / "config.json"
        cfg_path.write_text('{"key": "val"}', encoding="utf-8")

        result = load_user_config()

        assert result == {"key": "val"}

    def test_corrupt_config_file_returns_empty(self, mock_config_root: Path) -> None:
        """Broken JSON should not crash — gracefully return empty dict."""
        cfg_path = mock_config_root / "config.json"
        cfg_path.write_text("{invalid json!!!", encoding="utf-8")

        result = load_user_config()

        assert result == {}


class TestSaveUserConfig:

    def test_save_and_load_roundtrip(self, mock_config_root: Path) -> None:
        save_user_config({"a": 1, "b": "two"})
        result = load_user_config()

        assert result["a"] == 1
        assert result["b"] == "two"

    def test_save_merges_with_existing(self, mock_config_root: Path) -> None:
        save_user_config({"x": 1})
        save_user_config({"y": 2})
        result = load_user_config()

        assert result == {"x": 1, "y": 2}

    def test_save_deletes_key_with_none(self, mock_config_root: Path) -> None:
        """Passing None as value removes the key from config."""
        save_user_config({"a": 1, "b": 2, "c": 3})
        save_user_config({"b": None})
        result = load_user_config()

        assert result == {"a": 1, "c": 3}

    def test_save_delete_nonexistent_key_is_noop(self, mock_config_root: Path) -> None:
        """Deleting a key that doesn't exist does not raise."""
        save_user_config({"a": 1})
        save_user_config({"zzz": None})
        result = load_user_config()

        assert result == {"a": 1}


class TestUserRootDir:

    def test_get_user_root_dir_default(self, mock_config_root: Path) -> None:
        """No user_root_dir set → return None."""
        assert get_user_root_dir() is None

    def test_set_and_get_user_root_dir(
        self, mock_config_root: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "my_storage"
        set_user_root_dir(str(target))

        result = get_user_root_dir()

        assert result == target.resolve()
        assert target.is_dir()  # set_user_root_dir creates the directory
