from __future__ import annotations

import json
import os
import time
import threading
from pathlib import Path

import pytest

import runicorn as rn


def _read_assets(storage_root: Path, project: str, name: str, run_id: str) -> dict:
    p = storage_root / project / name / "runs" / run_id / "assets.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_outputs_scan_stability_and_rolling(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    out_dir = tmp_path / "outputs"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    f = out_dir / "last.pth"
    f.write_bytes(b"v1")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n", snapshot_code=False, workspace_root=str(workspace))

        r1 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="rolling",
        )
        assert r1["archived"] == 0

        r2 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="rolling",
        )
        assert r2["archived"] == 1

        assets = _read_assets(storage_root, "p", "n", run.id)
        assert len(assets.get("outputs") or []) == 1
        fp1 = assets["outputs"][0]["fingerprint"]
        ap1 = assets["outputs"][0]["archive_path"]

        f.write_bytes(b"v2")
        now = int(time.time()) + 5
        os.utime(f, (now, now))

        r3 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="rolling",
        )
        assert r3["archived"] == 0

        r4 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="rolling",
        )
        assert r4["archived"] == 1

        assets2 = _read_assets(storage_root, "p", "n", run.id)
        assert len(assets2.get("outputs") or []) == 1
        fp2 = assets2["outputs"][0]["fingerprint"]
        ap2 = assets2["outputs"][0]["archive_path"]
        assert fp2 != fp1
        assert ap2 == ap1

        run.finish()


def test_outputs_assets_json_no_lost_update_under_concurrency(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    out_dir = tmp_path / "outputs"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    f = out_dir / "final.pth"
    f.write_bytes(b"v1")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n6", snapshot_code=False, workspace_root=str(workspace))

        def _t1() -> None:
            run.log_dataset("ds", str(out_dir), save=False)

        def _t2() -> None:
            run.scan_outputs_once(
                output_dirs=[out_dir],
                patterns=["*.pth"],
                stable_required=1,
                min_age_sec=0.0,
                mode="rolling",
            )

        th1 = threading.Thread(target=_t1)
        th2 = threading.Thread(target=_t2)
        th1.start()
        th2.start()
        th1.join()
        th2.join()

        assets = _read_assets(storage_root, "p", "n6", run.id)
        assert len(assets.get("datasets") or []) == 1
        assert len(assets.get("outputs") or []) == 1

        run.finish()


def test_outputs_scan_respects_min_age(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    out_dir = tmp_path / "outputs"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    f = out_dir / "final.pth"
    f.write_bytes(b"v1")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n4", snapshot_code=False, workspace_root=str(workspace))

        r1 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=1,
            min_age_sec=10.0,
            mode="rolling",
        )
        assert r1["archived"] == 0

        old = int(time.time()) - 100
        os.utime(f, (old, old))

        r2 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=1,
            min_age_sec=10.0,
            mode="rolling",
        )
        assert r2["archived"] == 1

        run.finish()


def test_outputs_scan_log_snapshot_interval(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    out_dir = tmp_path / "outputs"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    f = out_dir / "train.log"
    f.write_text("line1\n", encoding="utf-8")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n5", snapshot_code=False, workspace_root=str(workspace))

        r1 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.log"],
            stable_required=100,
            min_age_sec=999.0,
            mode="rolling",
            log_snapshot_interval_sec=1000.0,
        )
        assert r1["archived"] == 1

        f.write_text("line1\nline2\n", encoding="utf-8")

        r2 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.log"],
            stable_required=100,
            min_age_sec=999.0,
            mode="rolling",
            log_snapshot_interval_sec=1000.0,
        )
        assert r2["archived"] == 0

        run.finish()


def test_outputs_scan_overwrite_versions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    out_dir = tmp_path / "outputs"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    f = out_dir / "last.pth"
    f.write_bytes(b"v1")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n2", snapshot_code=False, workspace_root=str(workspace))

        run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="overwrite_versions",
        )
        run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="overwrite_versions",
        )

        f.write_bytes(b"v2")
        now = int(time.time()) + 5
        os.utime(f, (now, now))

        run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="overwrite_versions",
        )
        run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["*.pth"],
            stable_required=2,
            min_age_sec=0.0,
            mode="overwrite_versions",
        )

        assets = _read_assets(storage_root, "p", "n2", run.id)
        assert len(assets.get("outputs") or []) == 2

        run.finish()


def test_outputs_scan_directory_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    workspace = tmp_path / "ws"
    out_dir = tmp_path / "outputs"

    storage_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    (workspace / "a.py").write_text("print('hi')\n", encoding="utf-8")

    ckpt_dir = out_dir / "ckpt"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    (ckpt_dir / "w.bin").write_bytes(b"x")

    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))

    with rn.enabled(True):
        run = rn.init(project="p", name="n3", snapshot_code=False, workspace_root=str(workspace))

        r1 = run.scan_outputs_once(
            output_dirs=[out_dir],
            patterns=["ckpt/"],
            stable_required=1,
            min_age_sec=0.0,
            mode="rolling",
        )
        assert r1["archived"] == 1

        assets = _read_assets(storage_root, "p", "n3", run.id)
        assert len(assets.get("outputs") or []) == 1
        assert assets["outputs"][0]["kind"] == "dir"

        run.finish()
