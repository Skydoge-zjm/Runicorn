[English](DEMO_EXAMPLES_GUIDE.md) | [简体中文](../zh/DEMO_EXAMPLES_GUIDE.md)

---

# Demo Examples Guide

## Overview

This guide introduces Runicorn's demo examples, demonstrating how to correctly use the SDK API for experiment tracking, model version management, deduplication storage, and lineage tracking.

## New Demo Code

### 1. `quickstart_demo.py` - Quick Start

**Simplest 5-minute introductory example**

```bash
python examples/quickstart_demo.py
```

**Features demonstrated**:
- ✅ Basic experiment initialization and completion
- ✅ Model artifact creation and saving
- ✅ Model loading and usage
- ✅ Automatic association between experiments and models

**Code characteristics**:
- Uses correct APIs: `rn.init()`, `run.summary()`, `run.finish()`
- Concise and clear, suitable for first-time users
- Complete minimal workflow

### 2. `complete_workflow_demo.py` - Complete Workflow

**Complete demo simulating real ML projects**

```bash
python examples/complete_workflow_demo.py
```

**Features demonstrated**:
- ✅ Experiment tracking and metrics logging (4 experiments)
- ✅ Model version control (3 model versions)
- ✅ **File-level deduplication** (shared pretrained weights)
- ✅ Bidirectional association between experiments and models
- ✅ Model usage and lineage tracking
- ✅ Model evaluation and fine-tuning

**Demo scenarios**:

1. **Scenario 1: Baseline Model Training**
   - Train ResNet-50 baseline model
   - Record training metrics (loss, accuracy)
   - Save model as v1

2. **Scenario 2: Improved Model Training**
   - Retrain with better hyperparameters
   - Create model v2 (shared pretrained weights)
   - Demonstrate performance improvements

3. **Scenario 3: Model Evaluation**
   - Load model v2 for evaluation
   - Record test set metrics
   - Determine if meets production standards

4. **Scenario 4: Task-Specific Fine-tuning**
   - Fine-tune based on model v2 for medical imaging
   - Create new model artifact
   - Demonstrate transfer learning

**Deduplication Effect (Two-File Model Structure)**:
- Each model contains 2 files:
  1. Shared weights file (~1.9 MB) - Same across all versions
  2. Fine-tuned weights file (~950 KB) - Unique per version
- All 3 model versions reuse the same shared weights file
- Through hard links, shared file stored only once
- Saves ~44% storage space (8.55 MB → 4.75 MB)
- Implemented via hard links (Windows same drive / Linux same filesystem)

## Core API Usage

### Correct Experiment Initialization and Completion

```python
import runicorn as rn

# Initialize experiment
run = rn.init(project="my_project", name="experiment_1")

# ... experiment code ...

# Finish experiment
run.finish()
```

**❌ Incorrect usage**:
```python
run.finish()  # Don't use this
```

### Recording Metrics

```python
# Record single step metrics
run.log(step=1, loss=0.5, accuracy=0.8)

# Record summary information
run.summary({
    "final_accuracy": 0.95,
    "training_time": 120
})
```

**❌ Incorrect usage**:
```python
run.summary(...)  # Don't use this
run.log_summary(...)  # Method doesn't exist
run.log_config(...)  # Method doesn't exist
```

### Creating and Saving Models

#### Single-File Model
```python
# Create artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})
artifact.add_tags("production", "v2")

# Save artifact (automatic version control)
version = run.log_artifact(artifact)
```

#### Two-File Model (Recommended, supports deduplication)
```python
# Create artifact with multiple files
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("shared_backbone.pth")     # Shared weights
artifact.add_file("task_head_v1.pth")        # Task-specific weights
artifact.add_metadata({
    "accuracy": 0.95,
    "files": {
        "backbone": "shared_backbone.pth",
        "head": "task_head_v1.pth"
    }
})

# Save artifact
version = run.log_artifact(artifact)
```

**Advantages of two-file structure**:
- ✅ Multiple versions share same backbone, deduplication saves space
- ✅ Only need to store different task head files
- ✅ Matches real ML scenarios (pretrained + fine-tuning)
- ✅ Can save 40-60% storage space

### Using Models

```python
# Load model (automatically records usage relationship)
artifact = run.use_artifact("my-model:latest")  # or "my-model:v2"
model_path = artifact.download()

# Get metadata
metadata = artifact.get_metadata()
accuracy = metadata.metadata.get('accuracy')
```

## File-Level Deduplication Principles

### Creating Models with Shared Components

```python
import random
import json
from pathlib import Path

def create_model_with_shared_weights(path, version):
    # Shared component (same across all versions)
    random.seed(42)  # Fixed seed
    shared_weights = [random.random() for _ in range(50000)]
    
    # Unique component (different per version)
    random.seed(version * 100)  # Different seed
    unique_weights = [random.random() for _ in range(25000)]
    
    model_data = {
        "shared": shared_weights,  # Shared
        "unique": unique_weights,  # Unique
        "version": version
    }
    
    with open(path, 'w') as f:
        json.dump(model_data, f)
```

### Deduplication Effect Calculation

- **Without dedup**: N versions × file size = total size
- **With dedup**: Shared component + N × unique component = total size
- **Space saved**: (without dedup - with dedup) / without dedup × 100%

**Example**:
- 3 model versions, each 2.85 MB
- Without dedup: 2.85 × 3 = 8.55 MB
- With dedup: 1.9 (shared) + 0.95×3 (unique) = 4.75 MB
- Savings: (8.55 - 4.75) / 8.55 = 44.4%

## Viewing Results

### Start Web UI

```bash
runicorn viewer --host 0.0.0.0 --port 5000
```

### Access Features

1. **Experiments List** (http://localhost:5000)
   - View "Artifacts Created" column
   - View "Artifacts Used" column

2. **Experiment Details**
   - Click experiment to enter details page
   - Switch to "Associated Artifacts" tab
   - View models created and used by this experiment

3. **Model Details**
   - Click model name to enter details
   - "Training History" tab: View experiments that created this model
   - "Performance Trends" tab: Compare performance across versions
   - "Lineage" tab: View model dependency graph

4. **Deduplication Statistics**
   - View dedup stats in top right of models page
   - Shows saved space and ratio

## Batch Execution

### Linux/Mac
```bash
chmod +x examples/run_all_demos.sh
./examples/run_all_demos.sh
```

### Windows
```cmd
examples\run_all_demos.bat
```

## Common Errors

### 1. API Call Errors

**❌ Incorrect**:
```python
run.log_config(params)  # Method doesn't exist
run.log_summary({...})  # Method doesn't exist
```

**✅ Correct**:
```python
run.summary({"hyperparameters": params})
run.summary({...})
```

### 2. File Cleanup

**Remember to clean up temporary files**:
```python
model_path.unlink()  # Delete temporary file
```

### 3. Deduplication Not Working

**Causes**:
- Windows: Files not on same drive
- Linux/Mac: Files not on same filesystem

**Solutions**:
- Ensure all files on same drive/filesystem
- Use absolute paths or paths relative to project

## Best Practices

1. **Experiment naming**: Use meaningful project and name
2. **Model naming**: Use consistent naming conventions
3. **Metadata**: Record complete hyperparameters and metrics
4. **Tags**: Use tags to mark important versions
5. **Description**: Add clear descriptions to artifacts
6. **Cleanup**: Clean up temporary files promptly

## Further Learning

- See `examples/test_artifacts.py` - Basic usage
- See `examples/user_workflow_demo.py` - Complete project
- See `deduplication_demo/` - Detailed dedup testing
- Read `docs/guides/en/ARTIFACTS_GUIDE.md` - Detailed documentation

## Summary

The new demo code corrects previous API usage errors and demonstrates:

✅ Correct SDK API usage
✅ Experiment tracking and metrics logging
✅ Model version control and management
✅ File-level deduplication effect (45% space savings)
✅ Association between experiments and models
✅ Complete lineage tracking

Through these examples, you can quickly master Runicorn's core features and apply them to real projects.

