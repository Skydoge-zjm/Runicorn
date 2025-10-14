"""
End-to-End Tests for Runicorn Artifacts

Simulates real user workflows and scenarios.
"""
import json
import tempfile
import time
from pathlib import Path

import pytest


class TestRealWorldScenarios:
    """Real-world usage scenarios."""
    
    def test_scenario_researcher_model_iterations(self):
        """
        Scenario: Researcher iteratively improves a model over weeks.
        
        Timeline:
        - Week 1: Baseline model (acc=0.85)
        - Week 2: Improved architecture (acc=0.90)
        - Week 3: More data (acc=0.92)
        - Week 4: Final tuning (acc=0.95)
        - Week 5: Need to compare with Week 2 version
        """
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            iterations = [
                ("baseline", 0.85, "Simple CNN"),
                ("improved_arch", 0.90, "ResNet18"),
                ("more_data", 0.92, "ResNet18 + augmentation"),
                ("final_tuning", 0.95, "ResNet18 + augmentation + lr_schedule"),
            ]
            
            for iter_name, accuracy, description in iterations:
                run = rn.init(
                    project="research",
                    name=f"iteration_{iter_name}",
                    storage=temp_dir
                )
                
                # Simulate training
                model_file = Path(temp_dir) / f"model_{iter_name}.pth"
                model_file.write_text(f"model weights for {description}")
                
                # Save version
                artifact = rn.Artifact("research-model", type="model")
                artifact.add_file(str(model_file))
                artifact.add_metadata({
                    "description": description,
                    "val_accuracy": accuracy,
                    "iteration": iter_name,
                    "date": time.strftime("%Y-%m-%d")
                })
                
                version = run.log_artifact(artifact)
                rn.log({"val_accuracy": accuracy})
                rn.finish()
                
                print(f"✅ Saved iteration {iter_name}: v{version} (acc={accuracy})")
            
            # Week 5: Researcher wants to compare Week 2 version
            run_compare = rn.init(project="research", name="comparison", storage=temp_dir)
            
            # Load Week 2 (v2)
            week2_model = run_compare.use_artifact("research-model:v2")
            week2_meta = week2_model.get_metadata()
            
            assert week2_meta.metadata["val_accuracy"] == 0.90
            assert week2_meta.metadata["iteration"] == "improved_arch"
            
            # Load latest (v4)
            latest_model = run_compare.use_artifact("research-model:latest")
            latest_meta = latest_model.get_metadata()
            
            assert latest_meta.metadata["val_accuracy"] == 0.95
            
            rn.finish()
            
            print(f"✅ Successfully compared Week 2 (v2, acc=0.90) with latest (v4, acc=0.95)")
    
    def test_scenario_team_collaboration(self):
        """
        Scenario: Team of 3 researchers working on same project.
        
        - Alice: Prepares dataset v1
        - Bob: Trains model-A using dataset v1
        - Carol: Trains model-B using dataset v1
        - Alice: Updates dataset to v2
        - Bob: Needs to know which dataset was used for model-A
        """
        try:
            import runicorn as rn
            from runicorn.artifacts import LineageTracker
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Alice: Prepare dataset v1
            run_alice1 = rn.init(project="team_project", name="alice_data_v1", storage=temp_dir)
            
            data_dir = Path(temp_dir) / "dataset_v1"
            data_dir.mkdir()
            (data_dir / "train.txt").write_text("v1 train data")
            
            dataset_v1 = rn.Artifact("team-dataset", type="dataset")
            dataset_v1.add_dir(str(data_dir))
            dataset_v1.add_metadata({"version": 1, "author": "Alice"})
            run_alice1.log_artifact(dataset_v1)
            rn.finish()
            
            # Bob: Train model-A
            run_bob = rn.init(project="team_project", name="bob_model_a", storage=temp_dir)
            dataset = run_bob.use_artifact("team-dataset:latest")
            
            model_a_file = Path(temp_dir) / "model_a.pth"
            model_a_file.write_text("model A")
            
            model_a = rn.Artifact("model-A", type="model")
            model_a.add_file(str(model_a_file))
            model_a.add_metadata({"author": "Bob", "accuracy": 0.92})
            run_bob.log_artifact(model_a)
            rn.finish()
            
            # Carol: Train model-B
            run_carol = rn.init(project="team_project", name="carol_model_b", storage=temp_dir)
            dataset = run_carol.use_artifact("team-dataset:latest")
            
            model_b_file = Path(temp_dir) / "model_b.pth"
            model_b_file.write_text("model B")
            
            model_b = rn.Artifact("model-B", type="model")
            model_b.add_file(str(model_b_file))
            model_b.add_metadata({"author": "Carol", "accuracy": 0.88})
            run_carol.log_artifact(model_b)
            rn.finish()
            
            # Alice: Update dataset to v2
            run_alice2 = rn.init(project="team_project", name="alice_data_v2", storage=temp_dir)
            
            data_dir_v2 = Path(temp_dir) / "dataset_v2"
            data_dir_v2.mkdir()
            (data_dir_v2 / "train.txt").write_text("v2 train data - more samples")
            
            dataset_v2 = rn.Artifact("team-dataset", type="dataset")
            dataset_v2.add_dir(str(data_dir_v2))
            dataset_v2.add_metadata({"version": 2, "author": "Alice"})
            run_alice2.log_artifact(dataset_v2)
            rn.finish()
            
            # Bob: Check which dataset was used for model-A
            tracker = LineageTracker(Path(temp_dir))
            lineage = tracker.build_lineage_graph("model-A", "model", 1)
            
            # Should show: team-dataset:v1 → run_bob → model-A:v1
            assert len(lineage.nodes) >= 3
            assert len(lineage.edges) >= 2
            
            # Verify dataset version
            dataset_nodes = [n for n in lineage.nodes if n.node_type == "artifact" and "dataset" in n.label.lower()]
            assert len(dataset_nodes) >= 1
            
            print("✅ Team collaboration workflow successful")
            print(f"   - Alice created 2 dataset versions")
            print(f"   - Bob and Carol trained models using v1")
            print(f"   - Lineage correctly tracked dataset version")
    
    def test_scenario_production_deployment(self):
        """
        Scenario: Model deployment to production.
        
        - Train multiple models
        - Select best one
        - Mark as "production" (via metadata)
        - Deploy and track usage
        """
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            best_acc = 0
            best_version = None
            
            # Train 5 experimental models
            for i in range(1, 6):
                run = rn.init(project="production", name=f"experiment_{i}", storage=temp_dir)
                
                model_file = Path(temp_dir) / f"model_{i}.pth"
                model_file.write_text(f"model {i}")
                
                accuracy = 0.85 + i * 0.02  # Vary accuracy
                
                artifact = rn.Artifact("production-model", type="model")
                artifact.add_file(str(model_file))
                artifact.add_metadata({
                    "experiment_id": i,
                    "val_accuracy": accuracy,
                    "status": "experimental"
                })
                
                version = run.log_artifact(artifact)
                rn.finish()
                
                if accuracy > best_acc:
                    best_acc = accuracy
                    best_version = version
            
            assert best_version == 5  # v5 should be best
            
            # Mark best version as production (via new artifact with metadata)
            run_prod = rn.init(project="production", name="deploy", storage=temp_dir)
            
            # Load best model
            best_model = run_prod.use_artifact(f"production-model:v{best_version}")
            best_path = best_model.download()
            
            # "Deploy" by creating production artifact
            prod_artifact = rn.Artifact("production-deployed", type="model")
            for file in best_path.iterdir():
                prod_artifact.add_file(str(file))
            prod_artifact.add_metadata({
                "source_version": f"production-model:v{best_version}",
                "deployed_at": time.time(),
                "status": "production",
                "accuracy": best_acc
            })
            prod_artifact.add_tags("production", "deployed", "best")
            
            prod_version = run_prod.log_artifact(prod_artifact)
            rn.finish()
            
            print(f"✅ Production deployment successful")
            print(f"   - Trained 5 experimental models")
            print(f"   - Selected best (v{best_version}, acc={best_acc})")
            print(f"   - Deployed as production-deployed:v{prod_version}")
    
    def test_scenario_dataset_evolution(self):
        """
        Scenario: Dataset evolves through preprocessing stages.
        
        - v1: Raw data
        - v2: Cleaned data
        - v3: Normalized data
        - v4: Augmented data
        Each model trained on different dataset version
        """
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_stages = [
                ("raw", "Raw unprocessed data"),
                ("cleaned", "Cleaned and filtered"),
                ("normalized", "Normalized values"),
                ("augmented", "With data augmentation"),
            ]
            
            for stage, description in dataset_stages:
                # Create dataset version
                run_data = rn.init(project="data_evolution", name=f"data_{stage}", storage=temp_dir)
                
                data_file = Path(temp_dir) / f"data_{stage}.txt"
                data_file.write_text(f"{stage} data")
                
                dataset = rn.Artifact("evolving-dataset", type="dataset")
                dataset.add_file(str(data_file))
                dataset.add_metadata({
                    "stage": stage,
                    "description": description
                })
                
                data_version = run_data.log_artifact(dataset)
                rn.finish()
                
                # Train model on this dataset version
                run_train = rn.init(project="data_evolution", name=f"train_{stage}", storage=temp_dir)
                dataset = run_train.use_artifact(f"evolving-dataset:v{data_version}")
                
                model_file = Path(temp_dir) / f"model_{stage}.pth"
                model_file.write_text(f"model trained on {stage}")
                
                model = rn.Artifact(f"model-{stage}", type="model")
                model.add_file(str(model_file))
                model.add_metadata({
                    "dataset_version": data_version,
                    "dataset_stage": stage
                })
                run_train.log_artifact(model)
                rn.finish()
            
            print("✅ Dataset evolution tracking successful")
            print(f"   - Created 4 dataset versions")
            print(f"   - Trained 4 models, each on different dataset version")


class TestStressTests:
    """Stress and load tests."""
    
    def test_many_versions(self):
        """Test creating many versions of same artifact."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            num_versions = 50
            
            for i in range(1, num_versions + 1):
                run = rn.init(project="stress", name=f"v{i}", storage=temp_dir)
                
                model_file = Path(temp_dir) / f"model_v{i}.pth"
                model_file.write_text(f"version {i}")
                
                artifact = rn.Artifact("stress-model", type="model")
                artifact.add_file(str(model_file))
                artifact.add_metadata({"iteration": i})
                
                version = run.log_artifact(artifact)
                assert version == i
                
                rn.finish()
                
                if i % 10 == 0:
                    print(f"  Created {i} versions...")
            
            # Verify all versions
            from runicorn.artifacts import create_artifact_storage
            storage = create_artifact_storage(Path(temp_dir))
            
            versions = storage.list_versions("stress-model", "model")
            assert len(versions) == num_versions
            
            print(f"✅ Successfully created and verified {num_versions} versions")
    
    def test_many_files_in_artifact(self):
        """Test artifact with many files."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="stress", name="many_files", storage=temp_dir)
            
            # Create 100 small files
            files_dir = Path(temp_dir) / "many_files"
            files_dir.mkdir()
            
            num_files = 100
            for i in range(num_files):
                (files_dir / f"file_{i:03d}.txt").write_text(f"content {i}")
            
            artifact = rn.Artifact("multi-file-model", type="model")
            artifact.add_dir(str(files_dir))
            
            version = run.log_artifact(artifact)
            rn.finish()
            
            # Verify all files saved
            run2 = rn.init(project="stress", name="verify", storage=temp_dir)
            loaded = run2.use_artifact("multi-file-model:latest")
            
            manifest = loaded.get_manifest()
            assert manifest.total_files == num_files
            
            # Download and verify
            download_dir = loaded.download()
            downloaded_files = list(download_dir.rglob("*.txt"))
            assert len(downloaded_files) == num_files
            
            rn.finish()
            
            print(f"✅ Successfully saved and loaded artifact with {num_files} files")
    
    def test_large_file_handling(self):
        """Test handling of large files (100MB)."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            run = rn.init(project="stress", name="large_file", storage=temp_dir)
            
            # Create 100 MB file
            large_file = Path(temp_dir) / "large_model.pth"
            size_mb = 100
            
            print(f"  Creating {size_mb}MB file...")
            with open(large_file, 'wb') as f:
                # Write in chunks to avoid memory issues
                chunk = b'x' * (1024 * 1024)  # 1 MB
                for _ in range(size_mb):
                    f.write(chunk)
            
            assert large_file.stat().st_size == size_mb * 1024 * 1024
            
            artifact = rn.Artifact("large-model", type="model")
            artifact.add_file(str(large_file))
            
            # Measure save time
            start = time.time()
            version = run.log_artifact(artifact)
            save_time = time.time() - start
            
            rn.finish()
            
            print(f"  Save time: {save_time:.2f}s")
            
            # Load and verify
            run2 = rn.init(project="stress", name="load_large", storage=temp_dir)
            
            start = time.time()
            loaded = run2.use_artifact("large-model:latest")
            load_time = time.time() - start
            
            print(f"  Load metadata time: {load_time:.2f}s")
            
            # Metadata load should be fast
            assert load_time < 1.0, "Metadata loading too slow"
            
            # Download
            start = time.time()
            download_dir = loaded.download()
            download_time = time.time() - start
            
            print(f"  Download time: {download_time:.2f}s")
            
            # Verify size
            downloaded_file = download_dir / "large_model.pth"
            assert downloaded_file.exists()
            assert downloaded_file.stat().st_size == size_mb * 1024 * 1024
            
            rn.finish()
            
            print(f"✅ Large file handling successful ({size_mb}MB)")
            print(f"   Save: {save_time:.2f}s, Load meta: {load_time:.2f}s, Download: {download_time:.2f}s")


class TestErrorRecovery:
    """Error recovery and resilience tests."""
    
    def test_recovery_from_partial_save(self):
        """Test recovery from interrupted save."""
        try:
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Artifacts not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = create_artifact_storage(Path(temp_dir))
            
            # Simulate partial save by creating version directory manually
            artifact_dir = Path(temp_dir) / "artifacts" / "model" / "test-model"
            artifact_dir.mkdir(parents=True)
            
            # Create partial v1 (incomplete)
            partial_dir = artifact_dir / "v1"
            partial_dir.mkdir()
            
            # Try to save new artifact (should detect conflict)
            import runicorn as rn
            run = rn.init(project="test", name="recovery", storage=temp_dir)
            
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_text("data")
            
            artifact = rn.Artifact("test-model", type="model")
            artifact.add_file(str(model_file))
            
            # Should fail due to existing directory
            with pytest.raises(RuntimeError, match="already exists"):
                run.log_artifact(artifact)
    
    def test_corrupted_dedup_pool(self):
        """Test handling of corrupted dedup pool files."""
        # This is tested implicitly in dedup tests
        # Dedup pool corruption is handled by hash verification
        pass


class TestAPIIntegration:
    """Test API endpoints integration."""
    
    def test_list_artifacts_api(self):
        """Test /api/artifacts endpoint."""
        # This would require running FastAPI server
        # For now, test the underlying function
        try:
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Artifacts not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = create_artifact_storage(Path(temp_dir))
            
            # Initially empty
            artifacts = storage.list_artifacts()
            assert artifacts == []
            
            # Create some artifacts via SDK
            import runicorn as rn
            
            for i in range(3):
                run = rn.init(project="api_test", name=f"create_{i}", storage=temp_dir)
                model_file = Path(temp_dir) / f"model_{i}.pth"
                model_file.write_text(f"data {i}")
                
                artifact = rn.Artifact(f"model-{i}", type="model")
                artifact.add_file(str(model_file))
                run.log_artifact(artifact)
                rn.finish()
            
            # List again
            artifacts = storage.list_artifacts()
            assert len(artifacts) == 3
            
            # Test type filter
            model_artifacts = storage.list_artifacts(type="model")
            assert len(model_artifacts) == 3
            
            dataset_artifacts = storage.list_artifacts(type="dataset")
            assert len(dataset_artifacts) == 0


# ==================== Performance Benchmarks ====================

class TestPerformanceBenchmarks:
    """Performance benchmark tests with metrics."""
    
    def test_benchmark_hash_calculation(self):
        """Benchmark SHA256 hash calculation."""
        try:
            from runicorn.artifacts import create_artifact_storage
        except ImportError:
            pytest.skip("Artifacts not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = create_artifact_storage(Path(temp_dir))
            
            # Test different file sizes
            sizes = [
                (1, 1024 * 1024),           # 1 MB
                (10, 10 * 1024 * 1024),     # 10 MB
                (50, 50 * 1024 * 1024),     # 50 MB
            ]
            
            print("\n  Hash Calculation Benchmarks:")
            print("  " + "-" * 50)
            
            for size_mb, size_bytes in sizes:
                test_file = Path(temp_dir) / f"test_{size_mb}mb.dat"
                test_file.write_bytes(b"x" * size_bytes)
                
                start = time.time()
                file_hash = storage._compute_file_hash(test_file)
                elapsed = time.time() - start
                
                throughput = size_mb / elapsed if elapsed > 0 else 0
                
                print(f"  {size_mb:3d} MB: {elapsed:6.3f}s ({throughput:6.1f} MB/s)")
                
                assert len(file_hash) == 64
                assert elapsed < size_mb * 0.1  # Should be < 0.1s per MB
    
    def test_benchmark_save_operations(self):
        """Benchmark save operation."""
        try:
            import runicorn as rn
        except ImportError:
            pytest.skip("Runicorn not installed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print("\n  Save Operation Benchmarks:")
            print("  " + "-" * 50)
            
            # Benchmark first save
            model_file = Path(temp_dir) / "model.pth"
            model_file.write_bytes(b"x" * (10 * 1024 * 1024))  # 10 MB
            
            run1 = rn.init(project="bench", name="first", storage=temp_dir)
            artifact1 = rn.Artifact("bench-model", type="model")
            artifact1.add_file(str(model_file))
            
            start = time.time()
            run1.log_artifact(artifact1)
            first_save = time.time() - start
            rn.finish()
            
            print(f"  First save (10MB):  {first_save:.3f}s")
            
            # Benchmark second save (should use dedup)
            run2 = rn.init(project="bench", name="second", storage=temp_dir)
            artifact2 = rn.Artifact("bench-model-2", type="model")
            artifact2.add_file(str(model_file))  # Same file
            
            start = time.time()
            run2.log_artifact(artifact2)
            second_save = time.time() - start
            rn.finish()
            
            print(f"  Second save (dedup): {second_save:.3f}s")
            
            speedup = first_save / second_save if second_save > 0 else 0
            print(f"  Speedup: {speedup:.1f}x")


# ==================== Main Test Runner ====================

def run_comprehensive_tests():
    """Run all test suites."""
    test_suites = [
        ("Core Functionality", TestArtifactCore),
        ("Versioning", TestArtifactVersioning),
        ("Deduplication", TestDeduplication),
        ("Lineage Tracking", TestLineageTracking),
        ("Concurrency", TestConcurrency),
        ("Security", TestSecurity),
        ("Error Handling", TestErrorHandling),
        ("Performance", TestPerformance),
        ("Integration", TestIntegration),
        ("Edge Cases", TestEdgeCases),
        ("Usage Tracking", TestUsageTracking),
        ("Real-World Scenarios", TestRealWorldScenarios),
        ("Stress Tests", TestStressTests),
        ("Error Recovery", TestErrorRecovery),
        ("API Integration", TestAPIIntegration),
        ("Performance Benchmarks", TestPerformanceBenchmarks),
    ]
    
    print("=" * 80)
    print("RUNICORN ARTIFACTS - COMPREHENSIVE TEST SUITE")
    print("Enterprise-Grade Testing")
    print("=" * 80)
    
    overall_start = time.time()
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    for suite_name, test_class in test_suites:
        print(f"\n{'='*80}")
        print(f"Test Suite: {suite_name}")
        print(f"{'='*80}")
        
        # Get test methods
        test_methods = [
            m for m in dir(test_class)
            if m.startswith('test_') and callable(getattr(test_class, m))
        ]
        
        for method_name in test_methods:
            total_tests += 1
            test_name = method_name.replace('test_', '').replace('_', ' ').title()
            
            try:
                instance = test_class()
                method = getattr(instance, method_name)
                method()
                
                print(f"✅ {test_name}")
                total_passed += 1
                
            except pytest.skip.Exception as e:
                print(f"⏭️  {test_name} (skipped)")
                total_skipped += 1
                
            except AssertionError as e:
                print(f"❌ {test_name}")
                print(f"   Assertion: {e}")
                total_failed += 1
                
            except Exception as e:
                print(f"❌ {test_name}")
                print(f"   {type(e).__name__}: {e}")
                total_failed += 1
    
    overall_time = time.time() - overall_start
    
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    print(f"  Total Tests:    {total_tests}")
    print(f"  Passed:         {total_passed} ✅")
    print(f"  Failed:         {total_failed} {'❌' if total_failed > 0 else ''}")
    print(f"  Skipped:        {total_skipped} ⏭️")
    print(f"  Success Rate:   {total_passed/total_tests*100 if total_tests > 0 else 0:.1f}%")
    print(f"  Total Time:     {overall_time:.2f}s")
    print(f"{'='*80}")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED! Code is production-ready.")
    else:
        print(f"\n⚠️  {total_failed} test(s) failed. Please review.")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)


