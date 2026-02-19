"""Tests for runicorn.sdk — asset methods (log_config, log_dataset, log_pretrained, scan_outputs)."""
from __future__ import annotations

import json
from pathlib import Path

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
