"""Tests for runicorn.sdk — asset methods (log_config, log_dataset, log_pretrained, scan_outputs)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from runicorn.sdk import Run


def _make_run(storage_root: Path, monkeypatch: pytest.MonkeyPatch, **kw) -> Run:
    monkeypatch.delenv("RUNICORN_DISABLE_MODERN_STORAGE", raising=False)
    monkeypatch.setenv("RUNICORN_DIR", str(storage_root))
    defaults = dict(path="test/assets", storage=str(storage_root),
                    capture_console=False, run_id="asset_001")
    defaults.update(kw)
    return Run(**defaults)


class TestLogConfig:
    def test_log_config_writes_assets_json(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """log_config() records config info into assets.json."""
        run = _make_run(storage_root, monkeypatch, run_id="cfg_001")
        try:
            run.log_config(args={"lr": 0.01, "batch_size": 32}, extra={"note": "test"})
            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            assert "config" in assets
            cfg = assets["config"]
            assert cfg["args"]["lr"] == 0.01
            assert cfg["extra"]["note"] == "test"
        finally:
            run.finish()

    def test_log_config_with_argparse_namespace(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """log_config accepts argparse.Namespace-like objects."""
        import argparse
        ns = argparse.Namespace(lr=0.001, epochs=10)
        run = _make_run(storage_root, monkeypatch, run_id="cfg_ns_001")
        try:
            run.log_config(args=ns)
            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            assert assets["config"]["args"]["lr"] == 0.001
            assert assets["config"]["args"]["epochs"] == 10
        finally:
            run.finish()

    def test_log_config_with_non_json_types(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """log_config handles Path, Enum, datetime, numpy scalars without crashing."""
        from enum import Enum

        class Optimizer(Enum):
            SGD = "sgd"
            ADAM = "adam"

        run = _make_run(storage_root, monkeypatch, run_id="cfg_nonjson_001")
        try:
            run.log_config(
                extra={
                    "data_dir": tmp_path / "data",
                    "optimizer": Optimizer.ADAM,
                    "started_at": datetime(2025, 3, 6, 12, 0, 0),
                },
            )
            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            cfg = assets["config"]["extra"]
            assert cfg["data_dir"] == str(tmp_path / "data")
            assert cfg["optimizer"] == "adam"
            assert cfg["started_at"] == "2025-03-06T12:00:00"
        finally:
            run.finish()


class TestLogDataset:
    def test_log_dataset_records_in_assets(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """log_dataset() writes dataset entry to assets.json."""
        ds_dir = tmp_path / "my_dataset"
        ds_dir.mkdir()
        (ds_dir / "train.csv").write_text("a,b\n1,2\n")

        run = _make_run(storage_root, monkeypatch, run_id="ds_001")
        try:
            run.log_dataset("cifar10", str(ds_dir), context="train", description="test dataset")
            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            assert "datasets" in assets
            assert len(assets["datasets"]) == 1
            ds = assets["datasets"][0]
            assert ds["name"] == "cifar10"
            assert ds["context"] == "train"
            assert ds["description"] == "test dataset"
            assert ds["saved"] is False  # save=False by default
        finally:
            run.finish()

    def test_log_dataset_with_dict_uri(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """log_dataset() accepts a dict as URI (e.g. for remote datasets)."""
        run = _make_run(storage_root, monkeypatch, run_id="ds_dict_001")
        try:
            run.log_dataset("hf_dataset", {"repo": "user/dataset", "split": "train"})
            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            ds = assets["datasets"][0]
            assert ds["name"] == "hf_dataset"
            assert ds["uri"]["repo"] == "user/dataset"
        finally:
            run.finish()


class TestScanOutputsOnce:
    def test_scan_outputs_once_archives_new_files(
        self, storage_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        """scan_outputs_once() discovers new files and records archived entries."""
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        (output_dir / "model.pth").write_bytes(b"\x00" * 128)

        run = _make_run(storage_root, monkeypatch, run_id="scan_001")
        try:
            result = run.scan_outputs_once(
                output_dirs=[str(output_dir)],
                patterns=["*.pth"],
                stable_required=1,
                min_age_sec=0,
            )
            assert isinstance(result, dict)
            assert result["scanned"] >= 1
        finally:
            run.finish()

    def test_scan_outputs_once_skips_sqlite_links_when_finished_during_scan(
        self,
        storage_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        run = _make_run(storage_root, monkeypatch, run_id="scan_skip_sqlite_001")
        try:
            assert run.storage_backend is not None

            def _fake_scan_outputs_once(**kwargs):
                run._finished = True
                run._outputs_watch_stop.set()
                return {
                    "run_id": run.id,
                    "scanned": 1,
                    "archived": 1,
                    "changed": 1,
                    "archived_entries": [
                        {
                            "key": "outputs/model.pth",
                            "name": "model.pth",
                            "kind": "file",
                            "path": "./outputs/model.pth",
                            "archive_path": str(storage_root / "archive" / "outputs" / "model.pth"),
                            "fingerprint_kind": "sha256",
                            "fingerprint": "abc",
                            "mode": "rolling",
                            "archived_at": 1,
                        }
                    ],
                }

            monkeypatch.setattr("runicorn.sdk.scan_outputs_once", _fake_scan_outputs_once)
            run.storage_backend.get_assets_for_run = MagicMock(return_value=[])
            run.storage_backend.unlink_run_asset = MagicMock()
            run.storage_backend.record_asset_for_run = MagicMock()

            result = run.scan_outputs_once(
                output_dirs=[str(storage_root / "outputs")],
                patterns=["*.pth"],
                stable_required=1,
                min_age_sec=0,
            )

            assert result["archived"] == 1
            run.storage_backend.unlink_run_asset.assert_not_called()
            run.storage_backend.record_asset_for_run.assert_not_called()
        finally:
            run.finish()


class TestLogPretrained:
    def test_log_pretrained_records_in_assets(self, storage_root: Path, monkeypatch: pytest.MonkeyPatch):
        """log_pretrained() writes pretrained entry to assets.json."""
        run = _make_run(storage_root, monkeypatch, run_id="pt_001")
        try:
            run.log_pretrained("resnet50", source_type="huggingface",
                               description="ImageNet pretrained")
            assets = json.loads(run._assets_path.read_text(encoding="utf-8"))
            assert "pretrained" in assets
            assert len(assets["pretrained"]) == 1
            pt = assets["pretrained"][0]
            assert pt["name"] == "resnet50"
            assert pt["source_type"] == "huggingface"
            assert pt["description"] == "ImageNet pretrained"
            assert pt["saved"] is False
        finally:
            run.finish()
