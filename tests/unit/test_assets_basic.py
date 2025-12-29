from __future__ import annotations

import json
from pathlib import Path

import pytest

import runicorn as rn


def test_init_snapshot_code_creates_assets_and_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n", snapshot_code=True, workspace_root=str(workspace))

    assets_path = storage_root / "p" / "n" / "runs" / run.id / "assets.json"
    assert assets_path.exists()

    assets = json.loads(assets_path.read_text(encoding="utf-8"))
    assert assets["code"]["snapshot"]["saved"] is True
    assert "archive_path" in assets["code"]["snapshot"]

    archive_path = Path(assets["code"]["snapshot"]["archive_path"])
    assert archive_path.exists()


def test_log_config_dataset_pretrained_write_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    ds = tmp_path / "dataset"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    ds.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")
    (ds / "x.txt").write_text("x\n", encoding="utf-8")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n", snapshot_code=False, workspace_root=str(workspace))
        run.log_config(args={"--config": "a"}, extra={"seed": 1}, config_files=["a.yaml"])
        run.log_dataset("ds", str(ds), save=False)
        run.log_pretrained("pt", path_or_uri=None, source_type="timm", save=False)

    assets_path = storage_root / "p" / "n" / "runs" / run.id / "assets.json"
    assets = json.loads(assets_path.read_text(encoding="utf-8"))

    assert assets["config"]["args"]["--config"] == "a"
    assert assets["config"]["extra"]["seed"] == 1
    assert len(assets["datasets"]) == 1
    assert assets["datasets"][0]["saved"] is False
    assert len(assets["pretrained"]) == 1
    assert assets["pretrained"][0]["saved"] is False
