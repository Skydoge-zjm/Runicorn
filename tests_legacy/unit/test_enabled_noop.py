from __future__ import annotations

from pathlib import Path

import pytest

import runicorn as rn
from runicorn.sdk import get_active_run


def test_init_returns_noop_when_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(False):
        run = rn.init(project="p", name="n")

    assert getattr(run, "id", None) == "disabled"
    assert get_active_run() is None
    assert not (storage_root / "p").exists()


def test_init_creates_dirs_when_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n")

    assert run.id != "disabled"
    assert (storage_root / "p").exists()
