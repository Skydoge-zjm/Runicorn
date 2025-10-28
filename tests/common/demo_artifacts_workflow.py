#!/usr/bin/env python3
"""
Artifacts Workflow Demo

Demonstrates complete artifacts workflow:
1. Training and saving models as artifacts
2. Loading artifacts for inference/fine-tuning
3. Version management
4. Lineage tracking
5. External references
"""
import sys
import json
import time
import random
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import runicorn as rn


def create_dummy_model_file(path: Path, model_type: str = "simple", size_mb: float = 1.0):
    """Create a dummy model file with random data."""
    # Create dummy model data (simulates PyTorch .pth or TensorFlow .h5)
    size_bytes = int(size_mb * 1024 * 1024)
    
    # Simple JSON format to simulate model
    model_data = {
        "type": model_type,
        "architecture": {
            "layers": [
                {"type": "conv2d", "filters": 64},
                {"type": "relu"},
                {"type": "maxpool"},
                {"type": "dense", "units": 128},
                {"type": "dropout", "rate": 0.5},
                {"type": "dense", "units": 10},
            ]
        },
        "weights": "binary_data_placeholder",
        "created_at": time.time()
    }
    
    # Write to file
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(model_data, f, indent=2)
        # Pad with comments to reach desired size
        remaining = size_bytes - path.stat().st_size
        if remaining > 0:
            f.write('\n# ' + 'x' * (remaining - 3))
    
    print(f"   Created dummy model: {path.name} ({size_mb:.2f} MB)")
    return path


def scenario_1_train_and_save_model():
    """
    Scenario 1: Train a model and save it as an artifact.
    
    This simulates a typical ML training workflow where you train a model
    and want to version it for future use.
    """
    print("\n" + "="*60)
    print("Scenario 1: Train and Save Model as Artifact")
    print("="*60)
    
    # Initialize training run
    run = rn.init(
        project="image_classification",
        name="resnet50_cifar10_v1",
        capture_env=True
    )
    
    print(f"✅ Started training run: {run.id}")
    
    # Log training config
    run.log({
        "model": "ResNet50",
        "dataset": "CIFAR-10",
        "batch_size": 128,
        "learning_rate": 0.001,
        "epochs": 50,
        "optimizer": "Adam",
    }, step=0)
    
    # Simulate training
    print(f"\n📊 Simulating training...")
    best_accuracy = 0
    for epoch in range(1, 51):
        time.sleep(0.05)
        
        # Simulate metrics
        loss = 2.5 * (0.9 ** epoch) + random.uniform(0, 0.1)
        accuracy = min(95.0, 60.0 + epoch * 0.7 + random.uniform(-1, 1))
        
        run.log({
            "train_loss": loss,
            "train_accuracy": accuracy,
        }, step=epoch)
        
        best_accuracy = max(best_accuracy, accuracy)
        
        if epoch % 10 == 0:
            print(f"   Epoch {epoch}/50 - Accuracy: {accuracy:.2f}%")
    
    # Training complete, save model
    print(f"\n💾 Saving model as artifact...")
    
    # Create temporary model file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Save model file
        model_path = tmpdir / "resnet50_cifar10.pth"
        create_dummy_model_file(model_path, "resnet50", size_mb=95.0)
        
        # Also save training config
        config_path = tmpdir / "training_config.json"
        config_data = {
            "model": "ResNet50",
            "dataset": "CIFAR-10",
            "epochs": 50,
            "best_accuracy": best_accuracy,
        }
        config_path.write_text(json.dumps(config_data, indent=2))
        print(f"   Created config: {config_path.name}")
        
        # Create artifact
        artifact = rn.Artifact("resnet50-cifar10", type="model")
        artifact.add_file(model_path)
        artifact.add_file(config_path, name="config.json")
        artifact.add_metadata({
            "architecture": "ResNet50",
            "dataset": "CIFAR-10",
            "accuracy": best_accuracy,
            "epochs": 50,
            "framework": "PyTorch",
            "input_size": [3, 224, 224],
            "num_classes": 10,
        })
        artifact.add_tags("production", "cifar10", "resnet")
        
        # Log artifact
        version = run.log_artifact(artifact)
        
        print(f"✅ Artifact saved: resnet50-cifar10:v{version}")
        print(f"   Metadata: accuracy={best_accuracy:.2f}%")
        print(f"   Files: 2 files")
    
    # Finish run
    run.summary({
        "final_accuracy": best_accuracy,
        "model_artifact": f"resnet50-cifar10:v{version}",
    })
    run.finish()
    
    print(f"✅ Training completed: {run.id}")
    return version


def scenario_2_load_and_use_model():
    """
    Scenario 2: Load a model artifact for inference.
    
    This shows how to load a previously saved model and use it.
    """
    print("\n" + "="*60)
    print("Scenario 2: Load Model for Inference")
    print("="*60)
    
    # Initialize inference run
    run = rn.init(
        project="image_classification",
        name="inference_batch_001",
        capture_env=True
    )
    
    print(f"✅ Started inference run: {run.id}")
    
    # Load model artifact
    print(f"\n📥 Loading model artifact...")
    
    try:
        artifact = run.use_artifact("resnet50-cifar10:latest")
        
        print(f"✅ Loaded artifact: {artifact.name}:v{artifact.version}")
        print(f"   Type: {artifact.type}")
        print(f"   Metadata:")
        for key, value in artifact.metadata.items():
            print(f"     - {key}: {value}")
        
        # Download artifact files
        print(f"\n📂 Downloading artifact files...")
        download_dir = artifact.download()
        print(f"   Downloaded to: {download_dir}")
        
        # List files
        files = list(download_dir.rglob("*"))
        print(f"   Files ({len(files)}):")
        for f in files:
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"     - {f.name} ({size_mb:.2f} MB)")
        
        # Simulate inference
        print(f"\n🔮 Running inference...")
        num_samples = 100
        for i in range(1, num_samples + 1):
            time.sleep(0.01)
            
            # Simulate prediction metrics
            confidence = random.uniform(0.85, 0.99)
            
            if i % 20 == 0:
                run.log({"avg_confidence": confidence}, step=i)
                print(f"   Processed {i}/{num_samples} samples")
        
        run.summary({
            "num_samples": num_samples,
            "avg_confidence": 0.92,
            "model_used": f"{artifact.name}:v{artifact.version}",
        })
        
    except FileNotFoundError:
        print(f"❌ Artifact not found!")
        print(f"   Run scenario_1 first to create the artifact.")
        run.finish(status="failed")
        return
    
    run.finish()
    print(f"✅ Inference completed: {run.id}")


def scenario_3_fine_tuning_new_version():
    """
    Scenario 3: Fine-tune existing model and save new version.
    
    This demonstrates loading an existing model, fine-tuning it,
    and saving it as a new version.
    """
    print("\n" + "="*60)
    print("Scenario 3: Fine-tune Model and Save New Version")
    print("="*60)
    
    # Initialize fine-tuning run
    run = rn.init(
        project="image_classification",
        name="resnet50_cifar10_finetuned",
        capture_env=True
    )
    
    print(f"✅ Started fine-tuning run: {run.id}")
    
    # Load base model
    print(f"\n📥 Loading base model...")
    
    try:
        base_artifact = run.use_artifact("resnet50-cifar10:latest")
        print(f"✅ Loaded base model: v{base_artifact.version}")
        print(f"   Base accuracy: {base_artifact.metadata.get('accuracy', 'N/A')}")
        
        # Download for fine-tuning
        base_model_dir = base_artifact.download()
        
        # Simulate fine-tuning
        print(f"\n🔧 Fine-tuning on new data...")
        run.log({
            "base_model": f"resnet50-cifar10:v{base_artifact.version}",
            "fine_tune_dataset": "CIFAR-10 + custom data",
            "learning_rate": 0.0001,  # Lower LR for fine-tuning
            "epochs": 10,
        }, step=0)
        
        best_accuracy = base_artifact.metadata.get('accuracy', 90.0)
        
        for epoch in range(1, 11):
            time.sleep(0.05)
            
            # Simulate improvement
            loss = 0.5 * (0.8 ** epoch) + random.uniform(0, 0.05)
            accuracy = best_accuracy + epoch * 0.3 + random.uniform(-0.5, 0.5)
            
            run.log({
                "fine_tune_loss": loss,
                "fine_tune_accuracy": accuracy,
            }, step=epoch)
            
            best_accuracy = max(best_accuracy, accuracy)
            
            if epoch % 5 == 0:
                print(f"   Epoch {epoch}/10 - Accuracy: {accuracy:.2f}%")
        
        # Save fine-tuned model as new version
        print(f"\n💾 Saving fine-tuned model...")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create fine-tuned model file
            model_path = tmpdir / "resnet50_cifar10_finetuned.pth"
            create_dummy_model_file(model_path, "resnet50_finetuned", size_mb=96.5)
            
            # Create artifact (same name, new version)
            artifact = rn.Artifact("resnet50-cifar10", type="model")
            artifact.add_file(model_path, name="model.pth")
            artifact.add_metadata({
                "architecture": "ResNet50",
                "dataset": "CIFAR-10 + custom",
                "accuracy": best_accuracy,
                "epochs": 10,
                "framework": "PyTorch",
                "base_version": base_artifact.version,
                "fine_tuned": True,
            })
            artifact.add_tags("production", "fine-tuned", "cifar10")
            
            # Log artifact (will create v2, v3, etc.)
            version = run.log_artifact(artifact)
            
            print(f"✅ Fine-tuned model saved: resnet50-cifar10:v{version}")
            print(f"   Base version: v{base_artifact.version}")
            print(f"   Improved accuracy: {best_accuracy:.2f}% (+{best_accuracy - base_artifact.metadata.get('accuracy', 0):.2f}%)")
        
        run.summary({
            "final_accuracy": best_accuracy,
            "base_version": base_artifact.version,
            "new_version": version,
            "improvement": best_accuracy - base_artifact.metadata.get('accuracy', 0),
        })
        
    except FileNotFoundError:
        print(f"❌ Base artifact not found!")
        run.finish(status="failed")
        return
    
    run.finish()
    print(f"✅ Fine-tuning completed: {run.id}")


def scenario_4_dataset_artifact():
    """
    Scenario 4: Save and load dataset artifacts.
    
    Demonstrates using artifacts for datasets with external references.
    """
    print("\n" + "="*60)
    print("Scenario 4: Dataset Artifact with External References")
    print("="*60)
    
    # Initialize data preparation run
    run = rn.init(
        project="datasets",
        name="cifar10_preprocessed",
        capture_env=True
    )
    
    print(f"✅ Started data preparation run: {run.id}")
    
    # Create dataset artifact
    print(f"\n📦 Creating dataset artifact...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create metadata file
        metadata_path = tmpdir / "dataset_info.json"
        dataset_info = {
            "name": "CIFAR-10 Preprocessed",
            "num_samples": 60000,
            "num_classes": 10,
            "image_size": [32, 32, 3],
            "preprocessing": [
                "normalize",
                "random_crop",
                "random_flip"
            ],
            "split": {
                "train": 50000,
                "test": 10000
            }
        }
        metadata_path.write_text(json.dumps(dataset_info, indent=2))
        
        # Create dataset artifact
        artifact = rn.Artifact("cifar10-preprocessed", type="dataset")
        artifact.add_file(metadata_path, name="info.json")
        
        # Add external reference (simulate large dataset on S3)
        artifact.add_reference(
            uri="s3://my-bucket/datasets/cifar10/train.tar.gz",
            checksum="sha256:abc123...",
            size=170000000,  # 170 MB
            name="train_data",
            split="train"
        )
        
        artifact.add_reference(
            uri="s3://my-bucket/datasets/cifar10/test.tar.gz",
            checksum="sha256:def456...",
            size=30000000,  # 30 MB
            name="test_data",
            split="test"
        )
        
        artifact.add_metadata({
            "dataset_name": "CIFAR-10",
            "total_samples": 60000,
            "num_classes": 10,
            "storage_type": "S3",
            "total_size_mb": 200,
        })
        artifact.add_tags("dataset", "vision", "cifar10")
        
        # Log artifact
        version = run.log_artifact(artifact)
        
        print(f"✅ Dataset artifact saved: cifar10-preprocessed:v{version}")
        print(f"   Local files: 1 file (info.json)")
        print(f"   External references: 2 references (S3)")
        print(f"   Total size: ~200 MB")
    
    run.finish()
    print(f"✅ Data preparation completed: {run.id}")


def scenario_5_multi_file_artifact():
    """
    Scenario 5: Save artifact with multiple files and directories.
    
    Demonstrates adding entire directories to artifacts.
    """
    print("\n" + "="*60)
    print("Scenario 5: Multi-File Artifact (Checkpoints)")
    print("="*60)
    
    # Initialize checkpoint run
    run = rn.init(
        project="training",
        name="bert_checkpoints",
        capture_env=True
    )
    
    print(f"✅ Started checkpoint run: {run.id}")
    
    # Create checkpoint artifact with multiple files
    print(f"\n📁 Creating checkpoint artifact...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create checkpoint directory structure
        checkpoint_dir = tmpdir / "checkpoint_epoch_10"
        checkpoint_dir.mkdir()
        
        # Create multiple files
        model_path = checkpoint_dir / "pytorch_model.bin"
        create_dummy_model_file(model_path, "bert", size_mb=440.0)
        
        config_path = checkpoint_dir / "config.json"
        config_path.write_text(json.dumps({
            "model_type": "bert",
            "hidden_size": 768,
            "num_layers": 12,
        }, indent=2))
        
        vocab_path = checkpoint_dir / "vocab.txt"
        vocab_path.write_text("word1\nword2\nword3\n...")
        
        training_args_path = checkpoint_dir / "training_args.bin"
        training_args_path.write_text("binary_data_placeholder")
        
        # Create artifact
        artifact = rn.Artifact("bert-base-checkpoint", type="model")
        
        # Add entire directory
        artifact.add_dir(
            checkpoint_dir,
            name="checkpoint_epoch_10",
            exclude_patterns=["*.tmp", "__pycache__"]
        )
        
        artifact.add_metadata({
            "model_type": "BERT",
            "epoch": 10,
            "checkpoint_size_mb": 440,
            "includes": ["model", "config", "vocab", "training_args"]
        })
        artifact.add_tags("bert", "checkpoint", "epoch-10")
        
        # Log artifact
        version = run.log_artifact(artifact)
        
        print(f"✅ Checkpoint artifact saved: bert-base-checkpoint:v{version}")
        print(f"   Files: 4 files in checkpoint_epoch_10/")
        print(f"   Total size: ~440 MB")
    
    run.finish()
    print(f"✅ Checkpoint saved: {run.id}")


def list_all_artifacts():
    """List all created artifacts (requires API client)."""
    print("\n" + "="*60)
    print("Summary: All Created Artifacts")
    print("="*60)
    
    try:
        import runicorn.api as api
        
        # Try to connect to viewer
        try:
            client = api.connect()
            artifacts = client.artifacts.list_artifacts()
            
            print(f"\n📦 Found {len(artifacts)} artifacts:")
            for artifact in artifacts:
                print(f"   - {artifact['name']} v{artifact['version']} ({artifact['type']})")
            
            client.close()
        except:
            print(f"\n💡 Start viewer to see all artifacts:")
            print(f"   runicorn viewer")
            print(f"   http://127.0.0.1:23300/artifacts")
    except ImportError:
        print(f"\n💡 View artifacts in the web UI:")
        print(f"   runicorn viewer")
        print(f"   http://127.0.0.1:23300/artifacts")


def main():
    """Run all scenarios."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║         Runicorn Artifacts Workflow Demo                 ║
║                                                           ║
║  This demo shows complete artifacts usage:               ║
║  • Saving models as versioned artifacts                  ║
║  • Loading artifacts for inference                       ║
║  • Fine-tuning and creating new versions                 ║
║  • Dataset artifacts with external references            ║
║  • Multi-file artifacts                                  ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    try:
        # Run scenarios
        print("Running 5 scenarios...")
        print("This will take about 30 seconds...\n")
        
        # Scenario 1: Train and save
        version1 = scenario_1_train_and_save_model()
        time.sleep(0.5)
        
        # Scenario 2: Load and use
        scenario_2_load_and_use_model()
        time.sleep(0.5)
        
        # Scenario 3: Fine-tune
        scenario_3_fine_tuning_new_version()
        time.sleep(0.5)
        
        # Scenario 4: Dataset
        scenario_4_dataset_artifact()
        time.sleep(0.5)
        
        # Scenario 5: Multi-file
        scenario_5_multi_file_artifact()
        
        # Summary
        list_all_artifacts()
        
        print("\n" + "="*60)
        print("✅ All scenarios completed successfully!")
        print("="*60)
        print(f"\n📚 What you learned:")
        print(f"   1. Create artifacts with run.log_artifact()")
        print(f"   2. Load artifacts with run.use_artifact()")
        print(f"   3. Download artifact files with artifact.download()")
        print(f"   4. Version management (v1, v2, v3...)")
        print(f"   5. Add metadata and tags")
        print(f"   6. External references for large data")
        print(f"   7. Multi-file and directory artifacts")
        print(f"\n💡 View in Web UI:")
        print(f"   runicorn viewer")
        print(f"   http://127.0.0.1:23300/artifacts")
        print(f"\n📖 Documentation:")
        print(f"   docs/guides/zh/ARTIFACTS_GUIDE.md")
        print("")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
