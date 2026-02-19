"""Unit tests for runicorn.extensions.experiment."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from runicorn.extensions.experiment import ExperimentManager, ExperimentMetadata


class TestExperimentManager:
    """ExperimentManager — add, search, tag, delete."""

    def test_add_and_search(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="proj", name="exp1", tags=["baseline"])
        mgr.add_experiment("r2", project="proj", name="exp2", tags=["ablation"])

        results = mgr.search_experiments(project="proj")
        assert len(results) == 2

    def test_search_by_tag(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="e1", tags=["gpu", "v100"])
        mgr.add_experiment("r2", project="p", name="e2", tags=["cpu"])

        results = mgr.search_experiments(tags=["gpu"])
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_search_by_text(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="resnet50", description="ImageNet training")
        mgr.add_experiment("r2", project="p", name="vit", description="ViT fine-tune")

        results = mgr.search_experiments(text="resnet")
        assert len(results) == 1
        assert results[0].name == "resnet50"

    def test_tag_experiment(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="e", tags=["a"])

        ok = mgr.tag_experiment("r1", ["b", "c"], append=True)
        assert ok is True
        meta = mgr.metadata["r1"]
        assert set(meta.tags) == {"a", "b", "c"}

    def test_tag_nonexistent_returns_false(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        assert mgr.tag_experiment("nope", ["x"]) is False

    def test_delete_experiment(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="e")
        result = mgr.delete_experiments(["r1"])
        assert result["r1"] is True
        assert "r1" not in mgr.metadata

    def test_delete_pinned_blocked(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="e")
        mgr.pin_experiment("r1")
        result = mgr.delete_experiments(["r1"])
        assert result["r1"] is False
        assert "r1" in mgr.metadata

    def test_delete_pinned_forced(self, tmp_path: Path):
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="e")
        mgr.pin_experiment("r1")
        result = mgr.delete_experiments(["r1"], force=True)
        assert result["r1"] is True

    def test_find_run_path_new_layout(self, tmp_path: Path):
        """_find_run_path finds run in new layout."""
        mgr = ExperimentManager(tmp_path)
        new_dir = tmp_path / "runs" / "proj" / "exp" / "r1"
        new_dir.mkdir(parents=True)

        found = mgr._find_run_path("proj", "exp", "r1")
        assert found == new_dir

    def test_find_run_path_old_layout(self, tmp_path: Path):
        """_find_run_path falls back to old layout."""
        mgr = ExperimentManager(tmp_path)
        old_dir = tmp_path / "proj" / "exp" / "runs" / "r1"
        old_dir.mkdir(parents=True)

        found = mgr._find_run_path("proj", "exp", "r1")
        assert found == old_dir

    def test_metadata_persists(self, tmp_path: Path):
        """Metadata survives reload from disk."""
        mgr = ExperimentManager(tmp_path)
        mgr.add_experiment("r1", project="p", name="e", tags=["t1"])

        mgr2 = ExperimentManager(tmp_path)
        assert "r1" in mgr2.metadata
        assert mgr2.metadata["r1"].tags == ["t1"]
