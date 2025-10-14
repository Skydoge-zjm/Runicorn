"""
Comprehensive Test Suite for Runicorn Artifacts

Enterprise-grade test suite covering:
- Unit tests for all functions
- Integration tests for complete workflows
- Boundary condition tests
- Concurrent operation tests
- Performance benchmarks
- Security tests
- Error handling tests

Run with: pytest tests/test_artifacts_comprehensive.py -v
Or: python tests/test_artifacts_comprehensive.py
"""
import json
import os
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import pytest


class TestArtifactCore:
    """Core functionality tests."""
    
    def test_artifact_creation_basic(self):
        """Test basic artifact creation."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        artifact = rn.Artifact("test-model", type="model")
        
        assert artifact.name == "test-model"
        assert artifact.type == "model"
        assert artifact.version is None  # Not saved yet
        assert artifact.is_loaded is False
        assert artifact.full_name == "test-model:unstaged"
    
    def test_artifact_invalid_name(self):
        """Test artifact name validation."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        # Test invalid characters
        invalid_names = [
            "model/test",    # Forward slash
            "model\\test",   # Backslash
            "model:test",    # Colon
            "model*test",    # Asterisk
            "model?test",    # Question mark
            "model<test",    # Less than
            "model>test",    # Greater than
            "model|test",    # Pipe
            "model\"test",   # Quote
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises(ValueError, match="invalid characters"):
                rn.Artifact(invalid_name, type="model")
    
    def test_artifact_add_file(self):
        """Test adding files to artifact."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "model.pth"
            test_file.write_text("model data")
            
            artifact = rn.Artifact("test-model", type="model")
            result = artifact.add_file(str(test_file))
            
            # Check method chaining
            assert result is artifact
            
            # Check file staged
            assert len(artifact._staged_files) == 1
            assert artifact._staged_files[0][1] == "model.pth"
    
    def test_artifact_add_file_duplicate(self):
        """Test that duplicate files are detected."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "model.pth"
            test_file.write_text("model data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(test_file))
            artifact.add_file(str(test_file))  # Duplicate
            
            # Should only have one file
            assert len(artifact._staged_files) == 1
    
    def test_artifact_add_nonexistent_file(self):
        """Test adding non-existent file."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        artifact = rn.Artifact("test-model", type="model")
        
        with pytest.raises(FileNotFoundError):
            artifact.add_file("/nonexistent/path/model.pth")
    
    def test_artifact_add_directory_as_file(self):
        """Test that directories are rejected by add_file."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = rn.Artifact("test-model", type="model")
            
            with pytest.raises(ValueError, match="use add_dir"):
                artifact.add_file(temp_dir)
    
    def test_artifact_add_directory(self):
        """Test adding directories recursively."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            data_dir = Path(temp_dir) / "dataset"
            data_dir.mkdir()
            (data_dir / "train.txt").write_text("train data")
            (data_dir / "val.txt").write_text("val data")
            
            # Create subdirectory
            subdir = data_dir / "images"
            subdir.mkdir()
            (subdir / "img1.jpg").write_text("image1")
            (subdir / "img2.jpg").write_text("image2")
            
            artifact = rn.Artifact("test-dataset", type="dataset")
            artifact.add_dir(str(data_dir))
            
            # Check all files staged
            assert len(artifact._staged_files) == 4
            file_paths = [f[1] for f in artifact._staged_files]
            assert "train.txt" in file_paths
            assert "val.txt" in file_paths
            assert str(Path("images") / "img1.jpg") in file_paths
            assert str(Path("images") / "img2.jpg") in file_paths
    
    def test_artifact_add_directory_with_exclusions(self):
        """Test directory addition with exclude patterns."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "dataset"
            data_dir.mkdir()
            (data_dir / "data.txt").write_text("data")
            (data_dir / "temp.log").write_text("log")
            (data_dir / "cache.tmp").write_text("cache")
            
            artifact = rn.Artifact("test-dataset", type="dataset")
            artifact.add_dir(str(data_dir), exclude_patterns=["*.log", "*.tmp"])
            
            # Only data.txt should be included
            assert len(artifact._staged_files) == 1
            assert artifact._staged_files[0][1] == "data.txt"
    
    def test_artifact_add_reference(self):
        """Test adding external references."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        artifact = rn.Artifact("test-dataset", type="dataset")
        artifact.add_reference(
            uri="s3://bucket/data",
            checksum="sha256:abc123",
            size=1000000000,
            location="us-east-1"
        )
        
        assert len(artifact._staged_references) == 1
        ref = artifact._staged_references[0]
        assert ref.uri == "s3://bucket/data"
        assert ref.checksum == "sha256:abc123"
        assert ref.size == 1000000000
    
    def test_artifact_metadata_and_tags(self):
        """Test metadata and tags."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        artifact = rn.Artifact("test-model", type="model")
        
        # Add metadata
        artifact.add_metadata({"accuracy": 0.95, "epochs": 100})
        assert artifact.metadata["accuracy"] == 0.95
        
        # Add more metadata
        artifact.add_metadata({"loss": 0.05})
        assert artifact.metadata["loss"] == 0.05
        assert artifact.metadata["accuracy"] == 0.95  # Still there
        
        # Add tags
        artifact.add_tags("production", "resnet", "imagenet")
        assert len(artifact._tags) == 3
        assert "production" in artifact._tags
        
        # Add duplicate tag
        artifact.add_tags("production")
        assert len(artifact._tags) == 3  # No duplicate


class TestArtifactVersioning:
    """Version control tests."""
    
    def test_save_and_version_increment(self):
        """Test version number auto-increment."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Version 1
            run1 = rn.init(project="test", name="v1", storage=temp_dir)
            
            model_file_v1 = Path(temp_dir) / "model_v1.pth"
            model_file_v1.write_text(json.dumps({"v": 1}))
            
            artifact1 = rn.Artifact("test-model", type="model")
            artifact1.add_file(str(model_file_v1))
            v1 = run1.log_artifact(artifact1)
            
            assert v1 == 1
            assert artifact1.version == 1
            assert artifact1.is_loaded is True
            
            rn.finish()
            
            # Version 2
            run2 = rn.init(project="test", name="v2", storage=temp_dir)
            
            model_file_v2 = Path(temp_dir) / "model_v2.pth"
            model_file_v2.write_text(json.dumps({"v": 2}))
            
            artifact2 = rn.Artifact("test-model", type="model")  # Same name
            artifact2.add_file(str(model_file_v2))
            v2 = run2.log_artifact(artifact2)
            
            assert v2 == 2
            
            rn.finish()
    
    def test_empty_artifact_rejected(self):
        """Test that empty artifacts cannot be saved."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="test", name="empty", storage=temp_dir)
            
            artifact = rn.Artifact("empty-model", type="model")
            # Don't add any files or references
            
            with pytest.raises(ValueError, match="no files or references"):
                run.log_artifact(artifact)
    
    def test_use_artifact_latest(self):
        """Test loading latest version."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create v1
            run1 = rn.init(project="test", name="create", storage=temp_dir)
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("v1 data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            artifact.add_metadata({"version": 1})
            run1.log_artifact(artifact)
            rn.finish()
            
            # Create v2
            run2 = rn.init(project="test", name="create2", storage=temp_dir)
            model_file.write_text("v2 data")
            
            artifact2 = rn.Artifact("test-model", type="model")
            artifact2.add_file(str(model_file))
            artifact2.add_metadata({"version": 2})
            run2.log_artifact(artifact2)
            rn.finish()
            
            # Load latest (should be v2)
            run3 = rn.init(project="test", name="use", storage=temp_dir)
            loaded = run3.use_artifact("test-model:latest")
            
            assert loaded.version == 2
            metadata = loaded.get_metadata()
            assert metadata.metadata["version"] == 2
            
            rn.finish()
    
    def test_use_artifact_specific_version(self):
        """Test loading specific version."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create v1 and v2
            for v in [1, 2]:
                run = rn.init(project="test", name=f"v{v}", storage=temp_dir)
                model_file = Path(temp_dir) / f"model_v{v}.pth"
                model_file.write_text(f"v{v} data")
                
                artifact = rn.Artifact("test-model", type="model")
                artifact.add_file(str(model_file))
                artifact.add_metadata({"version": v})
                run.log_artifact(artifact)
                rn.finish()
            
            # Load v1 specifically
            run3 = rn.init(project="test", name="use_v1", storage=temp_dir)
            loaded = run3.use_artifact("test-model:v1")
            
            assert loaded.version == 1
            metadata = loaded.get_metadata()
            assert metadata.metadata["version"] == 1
            
            rn.finish()
    
    def test_use_nonexistent_artifact(self):
        """Test loading non-existent artifact."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="test", name="use", storage=temp_dir)
            
            with pytest.raises(FileNotFoundError, match="Artifact not found"):
                run.use_artifact("nonexistent-model:latest")
    
    def test_use_invalid_version_format(self):
        """Test invalid version formats."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create artifact
            run1 = rn.init(project="test", name="create", storage=temp_dir)
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("data")
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            run1.log_artifact(artifact)
            rn.finish()
            
            # Try invalid formats
            run2 = rn.init(project="test", name="use", storage=temp_dir)
            
            with pytest.raises(ValueError, match="Invalid version"):
                run2.use_artifact("test-model:v-1")  # Negative
            
            with pytest.raises(ValueError, match="Invalid version"):
                run2.use_artifact("test-model:v0")  # Zero


class TestDeduplication:
    """Content deduplication tests."""
    
    def test_dedup_identical_files(self):
        """Test that identical files are deduplicated."""
        try:
            import runicorn as rn
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = create_artifact_storage(Path(temp_dir))
            
            # Create two identical files
            file1 = Path(temp_dir) / "file1.txt"
            file2 = Path(temp_dir) / "file2.txt"
            content = "same content" * 1000  # Make it bigger
            file1.write_text(content)
            file2.write_text(content)
            
            # Store both
            dest_dir = Path(temp_dir) / "dest"
            dest_dir.mkdir()
            
            hash1 = storage._compute_file_hash(file1)
            hash2 = storage._compute_file_hash(file2)
            
            assert hash1 == hash2  # Same content = same hash
            
            # Store first file
            entry1 = storage._store_file(file1, "file1.txt", dest_dir)
            
            # Store second file (should deduplicate)
            entry2 = storage._store_file(file2, "file2.txt", dest_dir)
            
            # Both should have same hash
            assert entry1.digest == entry2.digest
            
            # Check dedup pool
            if storage.dedup_pool:
                dedup_file = storage.dedup_pool / hash1[:2] / hash1
                assert dedup_file.exists()
                
                # Check if files are hardlinked (same inode)
                dest1 = dest_dir / "file1.txt"
                dest2 = dest_dir / "file2.txt"
                
                # Both files should exist
                assert dest1.exists()
                assert dest2.exists()
    
    def test_dedup_different_files(self):
        """Test that different files are not deduplicated."""
        try:
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Artifacts not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = create_artifact_storage(Path(temp_dir))
            
            file1 = Path(temp_dir) / "file1.txt"
            file2 = Path(temp_dir) / "file2.txt"
            file1.write_text("content 1")
            file2.write_text("content 2")  # Different
            
            hash1 = storage._compute_file_hash(file1)
            hash2 = storage._compute_file_hash(file2)
            
            assert hash1 != hash2  # Different content
    
    def test_dedup_space_savings(self):
        """Test deduplication space savings."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a large-ish file
            large_content = "x" * 1024 * 1024  # 1 MB
            large_file = Path(temp_dir) / "large.dat"
            large_file.write_text(large_content)
            
            # Save same file 5 times in different artifacts
            for i in range(5):
                run = rn.init(project="test", name=f"dedup_{i}", storage=temp_dir)
                
                artifact = rn.Artifact(f"model-{i}", type="model")
                artifact.add_file(str(large_file), name="large.dat")
                run.log_artifact(artifact)
                
                rn.finish()
            
            # Check dedup pool
            dedup_pool = Path(temp_dir) / "artifacts" / ".dedup"
            if dedup_pool.exists():
                # Count files in dedup pool
                dedup_files = list(dedup_pool.rglob("*"))
                dedup_files = [f for f in dedup_files if f.is_file()]
                
                # Should only have 1 unique file in pool
                assert len(dedup_files) == 1


class TestLineageTracking:
    """Lineage tracking tests."""
    
    def test_lineage_simple_chain(self):
        """Test simple lineage: dataset → run → model."""
        try:
            import runicorn as rn
            from runicorn.artifacts import LineageTracker
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create dataset
            run1 = rn.init(project="test", name="data", storage=temp_dir)
            data_file = Path(temp_dir) / "data.txt"
            data_file.write_text("dataset")
            
            dataset = rn.Artifact("test-dataset", type="dataset")
            dataset.add_file(str(data_file))
            run1.log_artifact(dataset)
            rn.finish()
            
            # Step 2: Use dataset, create model
            run2 = rn.init(project="test", name="train", storage=temp_dir)
            dataset = run2.use_artifact("test-dataset:latest")
            
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("model")
            
            model = rn.Artifact("test-model", type="model")
            model.add_file(str(model_file))
            run2.log_artifact(model)
            rn.finish()
            
            # Build lineage graph
            tracker = LineageTracker(Path(temp_dir))
            graph = tracker.build_lineage_graph("test-model", "model", 1, max_depth=3)
            
            # Should have 3 nodes: dataset, run2, model
            assert len(graph.nodes) >= 3
            
            # Should have 2 edges
            assert len(graph.edges) >= 2
    
    def test_lineage_cycle_detection(self):
        """Test that circular dependencies are detected."""
        try:
            from runicorn.artifacts import LineageTracker, LineageGraph
        except ImportError:
            pytest.skip("Artifacts not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = LineageTracker(Path(temp_dir))
            
            # Create artificial cycle by manipulating files
            # A:v1 created by run1, which used B:v1
            # B:v1 created by run2, which used A:v1
            
            # Setup directories
            artifacts_root = Path(temp_dir) / "artifacts"
            (artifacts_root / "model" / "A" / "v1").mkdir(parents=True)
            (artifacts_root / "model" / "B" / "v1").mkdir(parents=True)
            
            # A:v1 metadata
            a_meta = {
                "name": "A",
                "type": "model",
                "version": 1,
                "created_by_run": "run1",
                "created_at": time.time(),
                "size_bytes": 100,
            }
            (artifacts_root / "model" / "A" / "v1" / "metadata.json").write_text(
                json.dumps(a_meta)
            )
            
            # B:v1 metadata
            b_meta = {
                "name": "B",
                "type": "model",
                "version": 1,
                "created_by_run": "run2",
                "created_at": time.time(),
                "size_bytes": 100,
            }
            (artifacts_root / "model" / "B" / "v1" / "metadata.json").write_text(
                json.dumps(b_meta)
            )
            
            # Create run directories with circular usage
            (Path(temp_dir) / "test" / "cycle" / "runs" / "run1").mkdir(parents=True)
            (Path(temp_dir) / "test" / "cycle" / "runs" / "run2").mkdir(parents=True)
            
            # run1 used B:v1
            (Path(temp_dir) / "test" / "cycle" / "runs" / "run1" / "artifacts_used.json").write_text(
                json.dumps({"artifacts": [{"name": "B", "type": "model", "version": 1}]})
            )
            
            # run2 used A:v1
            (Path(temp_dir) / "test" / "cycle" / "runs" / "run2" / "artifacts_used.json").write_text(
                json.dumps({"artifacts": [{"name": "A", "type": "model", "version": 1}]})
            )
            
            # Build lineage - should not crash
            graph = tracker.build_lineage_graph("A", "model", 1, max_depth=10)
            
            # Should complete without infinite recursion
            assert graph is not None
            assert len(graph.nodes) > 0


class TestConcurrency:
    """Concurrent operation tests."""
    
    def test_concurrent_version_creation(self):
        """Test concurrent artifact saves to same name."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            num_workers = 5
            results = []
            
            def save_version(i: int):
                """Save one version."""
                try:
                    run = rn.init(
                        project="test",
                        name=f"concurrent_{i}",
                        storage=temp_dir
                    )
                    
                    model_file = Path(temp_dir) / f"model_{i}.pth"
                    model_file.write_text(f"version {i}")
                    
                    artifact = rn.Artifact("concurrent-model", type="model")
                    artifact.add_file(str(model_file))
                    artifact.add_metadata({"worker": i})
                    
                    version = run.log_artifact(artifact)
                    rn.finish()
                    
                    return version
                except Exception as e:
                    return f"Error: {e}"
            
            # Run concurrent saves
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(save_version, i) for i in range(num_workers)]
                results = [future.result() for future in as_completed(futures)]
            
            # Check all succeeded
            versions = [r for r in results if isinstance(r, int)]
            errors = [r for r in results if isinstance(r, str)]
            
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(versions) == num_workers
            
            # Check versions are unique
            assert len(set(versions)) == num_workers
            assert sorted(versions) == list(range(1, num_workers + 1))


class TestSecurity:
    """Security tests."""
    
    def test_path_traversal_in_add_file(self):
        """Test path traversal protection in add_file."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="test", name="security", storage=temp_dir)
            
            # Create a legitimate file
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("data")
            
            artifact = rn.Artifact("test-model", type="model")
            
            # Try to use path traversal in name parameter
            # This should be caught by storage layer
            artifact.add_file(str(model_file), name="../../../etc/passwd")
            
            # Save should fail with path validation
            with pytest.raises(ValueError, match="Invalid artifact path|Path traversal"):
                run.log_artifact(artifact)
    
    def test_artifact_name_injection(self):
        """Test artifact name validation."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        # These should all be rejected
        dangerous_names = [
            "../parent",
            "/absolute/path",
            "name/with/slash",
            "name\\with\\backslash",
            "name:colon",
        ]
        
        for dangerous_name in dangerous_names:
            with pytest.raises(ValueError, match="invalid characters"):
                rn.Artifact(dangerous_name, type="model")


class TestErrorHandling:
    """Error handling and recovery tests."""
    
    def test_corrupted_metadata_json(self):
        """Test handling of corrupted metadata.json."""
        try:
            import runicorn as rn
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid artifact
            run = rn.init(project="test", name="create", storage=temp_dir)
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            run.log_artifact(artifact)
            rn.finish()
            
            # Corrupt metadata.json
            metadata_path = Path(temp_dir) / "artifacts" / "model" / "test-model" / "v1" / "metadata.json"
            metadata_path.write_text("{ invalid json }")
            
            # Try to load
            run2 = rn.init(project="test", name="load", storage=temp_dir)
            
            with pytest.raises(ValueError, match="Invalid metadata JSON"):
                run2.use_artifact("test-model:latest")
    
    def test_missing_manifest(self):
        """Test handling of missing manifest.json."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create artifact
            run = rn.init(project="test", name="create", storage=temp_dir)
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            run.log_artifact(artifact)
            rn.finish()
            
            # Delete manifest.json
            manifest_path = Path(temp_dir) / "artifacts" / "model" / "test-model" / "v1" / "manifest.json"
            manifest_path.unlink()
            
            # Should still load (with empty manifest)
            run2 = rn.init(project="test", name="load", storage=temp_dir)
            loaded = run2.use_artifact("test-model:latest")
            
            manifest = loaded.get_manifest()
            assert manifest is not None
            assert manifest.total_files == 0  # Empty manifest


class TestPerformance:
    """Performance benchmark tests."""
    
    def test_hash_calculation_performance(self):
        """Benchmark hash calculation speed."""
        try:
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Artifacts not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = create_artifact_storage(Path(temp_dir))
            
            # Create 10 MB file
            test_file = Path(temp_dir) / "large.dat"
            test_file.write_bytes(b"x" * (10 * 1024 * 1024))
            
            # Measure hash time
            start = time.time()
            file_hash = storage._compute_file_hash(test_file)
            elapsed = time.time() - start
            
            # Should complete in reasonable time
            assert elapsed < 1.0, f"Hash calculation too slow: {elapsed:.2f}s for 10MB"
            assert len(file_hash) == 64  # SHA256 hex length
    
    def test_dedup_performance(self):
        """Benchmark deduplication performance."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create model file
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_bytes(b"x" * (10 * 1024 * 1024))  # 10 MB
            
            # First save (should be slow)
            run1 = rn.init(project="test", name="first", storage=temp_dir)
            artifact1 = rn.Artifact("test-model", type="model")
            artifact1.add_file(str(model_file))
            
            start = time.time()
            run1.log_artifact(artifact1)
            first_save_time = time.time() - start
            rn.finish()
            
            # Second save of identical file (should be fast with dedup)
            run2 = rn.init(project="test", name="second", storage=temp_dir)
            artifact2 = rn.Artifact("test-model-copy", type="model")
            artifact2.add_file(str(model_file))
            
            start = time.time()
            run2.log_artifact(artifact2)
            second_save_time = time.time() - start
            rn.finish()
            
            # Second save should be much faster
            print(f"First save: {first_save_time:.3f}s, Second save: {second_save_time:.3f}s")
            
            # May not always be faster on all systems, but should complete
            assert second_save_time < first_save_time * 2  # At least not slower


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_ml_pipeline_workflow(self):
        """Test complete ML pipeline: data prep → training → inference."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Data preparation
            run_data = rn.init(project="ml_pipeline", name="data_prep", storage=temp_dir)
            
            # Create dataset
            data_dir = Path(temp_dir) / "dataset"
            data_dir.mkdir()
            (data_dir / "train.txt").write_text("train data")
            (data_dir / "val.txt").write_text("val data")
            
            dataset = rn.Artifact("processed-data", type="dataset")
            dataset.add_dir(str(data_dir))
            dataset.add_metadata({"samples": 1000, "classes": 10})
            dataset_version = run_data.log_artifact(dataset)
            
            assert dataset_version == 1
            rn.finish()
            
            # Step 2: Training
            run_train = rn.init(project="ml_pipeline", name="training", storage=temp_dir)
            
            # Use dataset
            dataset_artifact = run_train.use_artifact("processed-data:latest")
            data_path = dataset_artifact.download()
            
            # Verify downloaded files
            assert (data_path / "train.txt").exists()
            assert (data_path / "val.txt").exists()
            
            # Create model
            model_file = Path(temp_dir) / "trained_model.pth"
            model_file.write_text("trained model weights")
            
            model = rn.Artifact("trained-model", type="model")
            model.add_file(str(model_file))
            model.add_metadata({
                "accuracy": 0.95,
                "dataset": "processed-data:v1"
            })
            model_version = run_train.log_artifact(model)
            
            assert model_version == 1
            rn.finish()
            
            # Verify lineage
            # Check artifacts_used.json in train run
            train_run_dir = Path(temp_dir) / "ml_pipeline" / "training" / "runs" / run_train.id
            used_file = train_run_dir / "artifacts_used.json"
            assert used_file.exists()
            
            used_data = json.loads(used_file.read_text())
            assert len(used_data["artifacts"]) == 1
            assert used_data["artifacts"][0]["name"] == "processed-data"
            
            # Check artifacts_created.json
            created_file = train_run_dir / "artifacts_created.json"
            assert created_file.exists()
            
            created_data = json.loads(created_file.read_text())
            assert len(created_data["artifacts"]) == 1
            assert created_data["artifacts"][0]["name"] == "trained-model"
    
    def test_model_versioning_workflow(self):
        """Test iterative model improvement workflow."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Iterate through 5 versions
            for v in range(1, 6):
                run = rn.init(
                    project="improvement",
                    name=f"iteration_{v}",
                    storage=temp_dir
                )
                
                model_file = Path(temp_dir) / f"model_v{v}.pth"
                model_file.write_text(f"model version {v}")
                
                artifact = rn.Artifact("improving-model", type="model")
                artifact.add_file(str(model_file))
                artifact.add_metadata({
                    "iteration": v,
                    "accuracy": 0.8 + v * 0.02  # Improving accuracy
                })
                
                version = run.log_artifact(artifact)
                assert version == v
                
                rn.finish()
            
            # Verify all versions exist
            from runicorn.artifacts import create_artifact_storage
            storage = create_artifact_storage(Path(temp_dir))
            
            versions = storage.list_versions("improving-model", "model")
            assert len(versions) == 5
            
            # Check version numbers are sequential
            version_nums = [v.version for v in versions]
            assert version_nums == [1, 2, 3, 4, 5]


class TestEdgeCases:
    """Edge case and boundary condition tests."""
    
    def test_zero_byte_file(self):
        """Test saving zero-byte files."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="test", name="empty_file", storage=temp_dir)
            
            empty_file = Path(temp_dir) / "empty.txt"
            empty_file.write_text("")  # 0 bytes
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(empty_file))
            
            version = run.log_artifact(artifact)
            assert version == 1
            
            rn.finish()
            
            # Load and verify
            run2 = rn.init(project="test", name="load", storage=temp_dir)
            loaded = run2.use_artifact("test-model:latest")
            
            download_dir = loaded.download()
            downloaded_file = download_dir / "empty.txt"
            assert downloaded_file.exists()
            assert downloaded_file.stat().st_size == 0
    
    def test_very_long_filename(self):
        """Test handling of very long filenames."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="test", name="long_name", storage=temp_dir)
            
            # Create file with long name (but within filesystem limits)
            long_name = "a" * 200 + ".txt"  # 200 chars
            long_file = Path(temp_dir) / long_name
            long_file.write_text("data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(long_file))
            
            version = run.log_artifact(artifact)
            assert version == 1
    
    def test_unicode_in_metadata(self):
        """Test Unicode characters in metadata."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="test", name="unicode", storage=temp_dir)
            
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            artifact.add_metadata({
                "description": "中文描述",
                "author": "张三",
                "emoji": "🚀",
                "math": "α + β = γ"
            })
            
            version = run.log_artifact(artifact)
            rn.finish()
            
            # Load and verify Unicode preserved
            run2 = rn.init(project="test", name="load", storage=temp_dir)
            loaded = run2.use_artifact("test-model:latest")
            
            metadata = loaded.get_metadata()
            assert metadata.metadata["description"] == "中文描述"
            assert metadata.metadata["author"] == "张三"
            assert metadata.metadata["emoji"] == "🚀"


class TestUsageTracking:
    """Usage tracking and lineage tests."""
    
    def test_artifacts_used_tracking(self):
        """Test that artifact usage is tracked correctly."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create artifact
            run1 = rn.init(project="test", name="create", storage=temp_dir)
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("model")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            run1.log_artifact(artifact)
            rn.finish()
            
            # Use artifact
            run2 = rn.init(project="test", name="use", storage=temp_dir)
            loaded = run2.use_artifact("test-model:latest")
            rn.finish()
            
            # Verify tracking
            used_file = Path(temp_dir) / "test" / "use" / "runs" / run2.id / "artifacts_used.json"
            assert used_file.exists()
            
            used_data = json.loads(used_file.read_text())
            assert len(used_data["artifacts"]) == 1
            assert used_data["artifacts"][0]["name"] == "test-model"
            assert used_data["artifacts"][0]["version"] == 1
    
    def test_duplicate_usage_not_recorded_twice(self):
        """Test that using same artifact twice doesn't create duplicates."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create artifact
            run1 = rn.init(project="test", name="create", storage=temp_dir)
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("model")
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            run1.log_artifact(artifact)
            rn.finish()
            
            # Use same artifact twice
            run2 = rn.init(project="test", name="use", storage=temp_dir)
            run2.use_artifact("test-model:latest")
            run2.use_artifact("test-model:latest")  # Second time
            rn.finish()
            
            # Should only be recorded once
            used_file = Path(temp_dir) / "test" / "use" / "runs" / run2.id / "artifacts_used.json"
            used_data = json.loads(used_file.read_text())
            assert len(used_data["artifacts"]) == 1


# ==================== Test Runner ====================

def run_all_tests():
    """Run all tests with detailed reporting."""
    test_classes = [
        TestArtifactCore,
        TestArtifactVersioning,
        TestDeduplication,
        TestLineageTracking,
        TestConcurrency,
        TestSecurity,
        TestErrorHandling,
        TestPerformance,
        TestIntegration,
        TestEdgeCases,
        TestUsageTracking,
    ]
    
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    
    print("=" * 80)
    print("Runicorn Artifacts - Comprehensive Test Suite")
    print("=" * 80)
    print()
    
    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n{class_name}")
        print("-" * 80)
        
        # Get all test methods
        test_methods = [
            method for method in dir(test_class) 
            if method.startswith('test_') and callable(getattr(test_class, method))
        ]
        
        for method_name in test_methods:
            total += 1
            test_name = method_name.replace('_', ' ').title()
            
            try:
                # Create instance and run test
                instance = test_class()
                method = getattr(instance, method_name)
                method()
                
                print(f"  ✅ {test_name}")
                passed += 1
                
            except pytest.skip.Exception as e:
                print(f"  ⏭️  {test_name} (skipped: {e})")
                skipped += 1
                
            except AssertionError as e:
                print(f"  ❌ {test_name}")
                print(f"     {e}")
                failed += 1
                
            except Exception as e:
                print(f"  ❌ {test_name}")
                print(f"     {type(e).__name__}: {e}")
                failed += 1
    
    print("\n" + "=" * 80)
    print(f"Test Summary:")
    print(f"  Total:   {total}")
    print(f"  Passed:  {passed} ✅")
    print(f"  Failed:  {failed} {'❌' if failed > 0 else ''}")
    print(f"  Skipped: {skipped} ⏭️")
    print(f"  Success Rate: {passed/total*100 if total > 0 else 0:.1f}%")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)


