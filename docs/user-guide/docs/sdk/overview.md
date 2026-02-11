# Python SDK Overview

The Runicorn Python SDK provides a simple, intuitive API for tracking ML experiments.

---

## Core Concepts

### Experiment Lifecycle

```mermaid
graph LR
    A[rn.init] --> B[run.log]
    B --> B
    B --> C[run.summary]
    C --> D[run.finish]
    
    style A fill:#52c41a
    style D fill:#52c41a
```

Every experiment follows this lifecycle:

1. **Initialize** - Create new experiment
2. **Log** - Record metrics during training
3. **Summary** - Save final results
4. **Finish** - Mark as complete

---

## Essential Functions

### `rn.init()` - Initialize Experiment

Create a new experiment run.

**Signature**:
```python
def init(
    project: str = "default",
    name: str = None,
    storage: str = None,
    run_id: str = None,
    capture_env: bool = True,
    capture_console: bool = False,  # v0.6.0
    tqdm_mode: str = "smart"        # v0.6.0
) -> Run
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project` | str | "default" | Project name (like a folder) |
| `name` | str | "default" | Experiment name (like sub-folder) |
| `storage` | str | None | Storage root path (overrides config) |
| `run_id` | str | None | Custom run ID (auto-generated if None) |
| `capture_env` | bool | True | Capture Git info, dependencies, system info |
| `capture_console` | bool | False | **v0.6.0** Capture stdout/stderr to logs.txt |
| `tqdm_mode` | str | "smart" | **v0.6.0** tqdm handling: "smart", "all", "none" |

**Returns**: `Run` object

**Example**:
```python
import runicorn as rn

# Simple
run = rn.init(project="demo")

# With name
run = rn.init(project="image_classification", name="resnet50_v1")

# With custom storage
run = rn.init(project="demo", storage="E:\\MLData")

# Without environment capture (faster)
run = rn.init(project="demo", capture_env=False)

# v0.6.0: With console capture
run = rn.init(project="demo", capture_console=True)
# All print() and stderr output will be saved to logs.txt

# v0.6.0: With tqdm handling
run = rn.init(project="demo", capture_console=True, tqdm_mode="smart")
# tqdm progress bars are intelligently filtered
```

---

### `run.log()` - Log Metrics

Record training metrics at each step.

**Signature**:
```python
def log(
    data: dict = None,
    step: int = None,
    stage: str = None,
    **kwargs
) -> None
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | dict | Dictionary of metric names and values |
| `step` | int | Training step (auto-increments if not provided) |
| `stage` | str | Training stage: "warmup", "train", "eval", etc. |
| `**kwargs` | any | Additional metrics as keyword arguments |

**Example**:
```python
import runicorn as rn

run = rn.init(project="demo")

# Simple logging
run.log({"loss": 0.5, "accuracy": 0.8}, step=10)

# Auto-incrementing step
run.log({"loss": 0.4})  # step=1
run.log({"loss": 0.3})  # step=2

# With stage
run.log({"loss": 0.2}, stage="train")
run.log({"val_loss": 0.3}, stage="eval")

# Using kwargs
run.log(loss=0.1, accuracy=0.95, lr=0.001, step=100)

# Mixed
run.log({"loss": 0.1}, accuracy=0.95, step=100)

run.finish()
```

---

### `run.log_text()` - Log Text Messages

Log text messages and progress updates.

**Signature**:
```python
def log_text(text: str) -> None
```

**Example**:
```python
import runicorn as rn

run = rn.init(project="demo")

run.log_text("Starting training...")
run.log_text(f"Epoch 1/100, loss=0.5")
run.log_text("✓ Training completed")

run.finish()
```

---

### `run.get_logging_handler()` - Python Logging Integration

**v0.6.0** Get a logging handler to integrate with Python's logging module.

**Signature**:
```python
def get_logging_handler(level: int = logging.INFO) -> logging.Handler
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | int | logging.INFO | Minimum log level to capture |

**Example**:
```python
import runicorn as rn
import logging

run = rn.init(project="demo")

# Add Runicorn handler to your logger
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler())
logger.setLevel(logging.INFO)

# Now all logging calls are saved to logs.txt
logger.info("Training started")
logger.warning("Learning rate is high")
logger.error("Out of memory")

run.finish()
```

---

### `run.log_image()` - Log Images

Log images for visualization.

**Signature**:
```python
def log_image(
    key: str,
    image: Any,
    step: int = None,
    caption: str = None,
    format: str = "png",
    quality: int = 90
) -> str
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | str | Image identifier/name |
| `image` | PIL.Image, np.ndarray, bytes, or path | Image to log |
| `step` | int | Training step |
| `caption` | str | Image caption |
| `format` | str | Image format: "png", "jpg" |
| `quality` | int | JPEG quality (1-100) |

**Example**:
```python
import runicorn as rn
from PIL import Image
import numpy as np

run = rn.init(project="demo")

# From PIL Image
img = Image.open("prediction.png")
run.log_image("prediction", img, step=100, caption="Model prediction")

# From numpy array
array = np.random.rand(224, 224, 3) * 255
run.log_image("sample", array.astype(np.uint8), step=100)

# From file path
run.log_image("result", "output.jpg", step=100)

run.finish()
```

---

### `run.set_primary_metric()` - Track Best Value

Set which metric to track automatically.

**Signature**:
```python
def set_primary_metric(
    metric_name: str,
    mode: str = "max"
) -> None
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `metric_name` | str | Metric to track (e.g., "accuracy", "loss") |
| `mode` | str | "max" (higher is better) or "min" (lower is better) |

**Example**:
```python
import runicorn as rn

run = rn.init(project="demo")

# Track best accuracy
run.set_primary_metric("accuracy", mode="max")

# Training loop
for step in range(100):
    acc = train_step()  # Your training code
    run.log({"accuracy": acc}, step=step)

# Best accuracy is automatically saved to summary
run.finish()
```

**Automatic tracking**: The best value and its step are automatically saved to `summary.json`.

---

### `run.summary()` - Save Summary

Record final results and metadata.

**Signature**:
```python
def summary(update: dict) -> None
```

**Example**:
```python
import runicorn as rn

run = rn.init(project="demo")

# Training...
for step in range(100):
    run.log({"loss": 0.1}, step=step)

# Save final results
run.summary({
    "final_accuracy": 0.95,
    "final_loss": 0.05,
    "total_epochs": 100,
    "dataset": "CIFAR-10",
    "model": "ResNet50",
    "notes": "Baseline experiment with default hyperparameters"
})

run.finish()
```

---

### `run.finish()` - Complete Experiment

Mark experiment as finished.

**Signature**:
```python
def finish(status: str = "finished") -> None
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | str | "finished" | Final status: "finished", "failed", "interrupted" |

**Example**:
```python
import runicorn as rn

run = rn.init(project="demo")

try:
    # Training code
    for step in range(100):
        run.log({"loss": 0.1}, step=step)
    
    # Success
    run.finish(status="finished")
    
except KeyboardInterrupt:
    # User interrupted
    run.finish(status="interrupted")
    
except Exception as e:
    # Training failed
    run.log_text(f"Error: {e}")
    run.finish(status="failed")
```

---

## v0.6.0 New Features

### Enhanced Logging

Automatically capture console output and integrate with Python logging:

```python
import runicorn as rn
import logging

# Enable console capture
run = rn.init(project="demo", capture_console=True, tqdm_mode="smart")

# All print() output is captured
print("Training started...")

# Integrate with Python logging
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler())
logger.info("Epoch 1 completed")

# tqdm progress bars are intelligently handled
from tqdm import tqdm
for i in tqdm(range(100)):
    train_step()

run.finish()
# All output is saved to logs.txt
```

**Learn more**: [Enhanced Logging Guide](../getting-started/enhanced-logging.md)

### Assets System

Snapshot your workspace with SHA256 content-addressed storage:

```python
import runicorn as rn

run = rn.init(project="demo")

# Snapshot entire workspace
manifest = rn.snapshot_workspace(
    run_id=run.id,
    include_patterns=["*.py", "config.yaml"],
    exclude_patterns=["*.pyc", "__pycache__"]
)

# Store individual blobs
blob_id = run.store_blob("model.pth")
model_path = run.get_blob_path(blob_id)

run.finish()
```

**Learn more**: [Assets System Guide](../getting-started/assets-system.md)

---

## Complete Example

Here's a complete experiment tracking a real PyTorch model:

```python
import runicorn as rn
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms

# Initialize
run = rn.init(
    project="image_classification",
    name="mnist_cnn",
    capture_env=True  # Capture Git, pip packages, system info
)

run.log_text("Starting MNIST training...")
run.set_primary_metric("test_accuracy", mode="max")

# Define model
model = nn.Sequential(
    nn.Conv2d(1, 32, 3, 1),
    nn.ReLU(),
    nn.MaxPool2d(2),
    nn.Flatten(),
    nn.Linear(5408, 10)
)

optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

# Load data
train_loader = torch.utils.data.DataLoader(
    datasets.MNIST('./data', train=True, download=True,
                   transform=transforms.ToTensor()),
    batch_size=64, shuffle=True
)

# Training loop
for epoch in range(10):
    model.train()
    total_loss = 0
    
    for batch_idx, (data, target) in enumerate(train_loader):
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
        # Log every 100 batches
        if batch_idx % 100 == 0:
            run.log({
                "train_loss": loss.item(),
                "learning_rate": optimizer.param_groups[0]['lr']
            }, stage="train")
    
    # Log epoch metrics
    avg_loss = total_loss / len(train_loader)
    run.log({"epoch_loss": avg_loss}, step=epoch)
    run.log_text(f"Epoch {epoch+1}/10, loss={avg_loss:.4f}")

# Save model
torch.save(model.state_dict(), "mnist_model.pth")

# Save as artifact
artifact = rn.Artifact("mnist-cnn", type="model")
artifact.add_file("mnist_model.pth")
artifact.add_metadata({
    "architecture": "Simple CNN",
    "epochs": 10,
    "optimizer": "Adam",
    "dataset": "MNIST"
})

version = run.log_artifact(artifact)
run.log_text(f"Model saved as v{version}")

# Summary
run.summary({
    "final_loss": avg_loss,
    "total_epochs": 10,
    "model_path": "mnist_model.pth"
})

run.finish()
print(f"✓ Experiment completed: {run.id}")
```

**Then view in browser**: `runicorn viewer` → [http://127.0.0.1:23300](http://127.0.0.1:23300)

---

## Common Patterns

### Pattern 1: Simple Training Loop

```python
import runicorn as rn

run = rn.init(project="demo", name="simple_training")
run.set_primary_metric("accuracy", mode="max")

for epoch in range(100):
    # Your training code
    loss, acc = train_one_epoch(model)
    
    # Log metrics
    run.log({"loss": loss, "accuracy": acc}, step=epoch)

run.finish()
```

### Pattern 2: Multi-Stage Training

```python
import runicorn as rn

run = rn.init(project="demo")

# Warmup stage
for step in range(10):
    run.log({"loss": 1.0}, step=step, stage="warmup")

# Training stage
for step in range(10, 100):
    run.log({"loss": 0.5}, step=step, stage="train")

# Evaluation stage
for step in range(100, 110):
    run.log({"val_loss": 0.3}, step=step, stage="eval")

run.finish()
```

### Pattern 3: Checkpoint Saving

```python
import runicorn as rn
import torch

run = rn.init(project="training")

for epoch in range(100):
    train_one_epoch(model)
    
    # Save checkpoint every 10 epochs
    if epoch % 10 == 0:
        # Save model
        checkpoint_path = f"checkpoint_epoch{epoch}.pth"
        torch.save(model.state_dict(), checkpoint_path)
        
        # Save as artifact
        artifact = rn.Artifact(f"model-checkpoint", type="model")
        artifact.add_file(checkpoint_path)
        artifact.add_metadata({"epoch": epoch})
        
        version = run.log_artifact(artifact)
        run.log_text(f"Checkpoint saved as v{version}")

run.finish()
```

---

## Best Practices

!!! tip "Tip: Organize Your Projects"

    Use a clear project/name hierarchy:
    
    ```python
    # Good
    rn.init(project="image_classification", name="resnet50_baseline")
    rn.init(project="image_classification", name="resnet50_augmented")
    rn.init(project="nlp", name="bert_finetuning")
    
    # Avoid
    rn.init(project="test", name="exp1")  # Not descriptive
    ```

!!! tip "Tip: Set Primary Metric"

    Always set a primary metric for easy comparison:
    
    ```python
    run.set_primary_metric("accuracy", mode="max")
    # Now best accuracy is automatically tracked
    ```

!!! warning "Remember to call finish()"

    Always call `run.finish()` at the end to ensure data is saved:
    
    ```python
    run = rn.init(project="demo")
    try:
        # Training code
        run.log({"loss": 0.1})
    finally:
        run.finish()  # Always called, even if error occurs
    ```

---

## Next Steps

- More SDK documentation coming soon
- For complete API reference, see the inline documentation in code
- For examples, see [Image Classification Tutorial](../tutorials/image-classification.md)

---

## Quick Reference

```python
import runicorn as rn

# Initialize
run = rn.init(project="demo", name="exp1")

# Set primary metric
run.set_primary_metric("accuracy", mode="max")

# Log metrics
run.log({"loss": 0.1, "accuracy": 0.95}, step=100, stage="train")

# Log text
run.log_text("Training started")

# Log image
run.log_image("prediction", image_array, step=100)

# Save artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
run.log_artifact(artifact)

# Summary
run.summary({"final_accuracy": 0.95})

# Finish
run.finish()
```

---

<div align="center">
  <p><a href="experiment-tracking.md">Learn More About Experiment Tracking →</a></p>
</div>

