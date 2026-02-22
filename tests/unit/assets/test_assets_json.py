"""Unit tests for runicorn.assets.assets_json."""
from __future__ import annotations

import json
from pathlib import Path

from filelock import FileLock

from runicorn.assets.assets_json import (
    ensure_assets_file,
    read_assets,
    update_assets_atomic,
)


class TestEnsureAssetsFile:
    """ensure_assets_file creates default structure if missing."""

    def test_creates_default(self, tmp_path: Path):
        p = tmp_path / "sub" / "assets.json"
        ensure_assets_file(p)
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "code" in data
        assert "datasets" in data
        assert isinstance(data["datasets"], list)

    def test_noop_if_exists(self, tmp_path: Path):
        p = tmp_path / "assets.json"
        p.write_text('{"custom": true}', encoding="utf-8")
        ensure_assets_file(p)
        assert json.loads(p.read_text(encoding="utf-8")) == {"custom": True}


class TestUpdateAssetsAtomic:
    """update_assets_atomic applies updater under lock."""

    def test_updates_existing(self, tmp_path: Path):
        p = tmp_path / "assets.json"
        lock = FileLock(str(p) + ".lock")

        p.write_text('{"code": {}}', encoding="utf-8")

        def add_entry(data):
            data["code"]["main.py"] = {"sha256": "abc123"}
            return data

        result = update_assets_atomic(p, lock, add_entry)
        assert result["code"]["main.py"]["sha256"] == "abc123"

        on_disk = json.loads(p.read_text(encoding="utf-8"))
        assert on_disk == result

    def test_creates_if_missing(self, tmp_path: Path):
        p = tmp_path / "new_assets.json"
        lock = FileLock(str(p) + ".lock")

        result = update_assets_atomic(p, lock, lambda d: {**d, "added": True})
        assert result["added"] is True
        assert p.exists()


class TestReadAssets:
    """read_assets returns empty dict if file missing."""

    def test_missing_returns_empty(self, tmp_path: Path):
        assert read_assets(tmp_path / "nope.json") == {}

    def test_reads_existing(self, tmp_path: Path):
        p = tmp_path / "a.json"
        p.write_text('{"k": 1}', encoding="utf-8")
        assert read_assets(p) == {"k": 1}
