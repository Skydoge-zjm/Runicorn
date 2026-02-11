# Enhanced Logging Guide

**New in v0.6.0** - Automatically capture console output and integrate with Python logging.

---

## Overview

Runicorn's Enhanced Logging system provides three powerful features:

1. **Console Capture** - Automatically save all `print()` and `stderr` output
2. **Python Logging Integration** - Connect your existing loggers to Runicorn
3. **Smart tqdm Handling** - Intelligently filter progress bars

All output is saved to `logs.txt` in your experiment directory.

---

## Quick Start

### Basic Console Capture

Capture all console output automatically:

```python
import runicorn as rn

# Enable console capture
run = rn.init(
    project="demo",
    capture_console=True
)

# All print() output is captured
print("Training started...")
print(f"Epoch 1/10, loss=0.5")
print("✓ Training completed")

run.finish()
# All output is saved to logs.txt
```

### Python Logging Integration

Connect your existing logger:

```python
import runicorn as rn
import logging

run = rn.init(project="demo")

# Get Runicorn's logging handler
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler())
logger.setLevel(logging.INFO)

# Now all logging calls are saved
logger.info("Training started")
logger.warning("Learning rate is high")
logger.error("Out of memory")

run.finish()
```

### Smart tqdm Handling

Automatically filter tqdm progress bars:

```python
import runicorn as rn
from tqdm import tqdm

run = rn.init(
    project="demo",
    capture_console=True,
    tqdm_mode="smart"  # Filter tqdm updates
)

# tqdm progress bars are intelligently handled
for epoch in tqdm(range(100), desc="Training"):
    for batch in tqdm(range(50), desc="Batches", leave=False):
        train_step()

run.finish()
# Only final tqdm states are saved, not every update
```

---

## tqdm Modes

Control how tqdm progress bars are captured:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `"smart"` | Only save final states | **Recommended** - Clean logs |
| `"all"` | Save every update | Debugging tqdm issues |
| `"none"` | Skip all tqdm output | Don't want progress bars in logs |

**Example**:

```python
# Smart mode (default) - Clean logs
run = rn.init(project="demo", capture_console=True, tqdm_mode="smart")

# All mode - Verbose logs
run = rn.init(project="demo", capture_console=True, tqdm_mode="all")

# None mode - No progress bars
run = rn.init(project="demo", capture_console=True, tqdm_mode="none")
```

---

## Complete Example

Here's a complete training script with enhanced logging:

```python
import runicorn as rn
import logging
from tqdm import tqdm
import torch
import torch.nn as nn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize with console capture
run = rn.init(
    project="image_classification",
    name="resnet50_training",
    capture_console=True,
    tqdm_mode="smart"
)

# Add Runicorn handler
logger.addHandler(run.get_logging_handler())

# Training setup
logger.info("Initializing model...")
model = nn.Sequential(
    nn.Conv2d(3, 64, 3),
    nn.ReLU(),
    nn.Flatten(),
    nn.Linear(64*30*30, 10)
)

logger.info("Starting training...")
print("=" * 50)
print("Training Configuration")
print("=" * 50)
print(f"Model: ResNet50")
print(f"Epochs: 100")
print(f"Batch size: 32")
print("=" * 50)

# Training loop with tqdm
for epoch in tqdm(range(100), desc="Epochs"):
    epoch_loss = 0
    
    for batch_idx in tqdm(range(50), desc="Batches", leave=False):
        # Training step
        loss = train_step(model)
        epoch_loss += loss
        
        # Log metrics
        run.log({"batch_loss": loss}, step=epoch * 50 + batch_idx)
    
    avg_loss = epoch_loss / 50
    run.log({"epoch_loss": avg_loss}, step=epoch)
    
    # Log progress
    if epoch % 10 == 0:
        logger.info(f"Epoch {epoch}/100, loss={avg_loss:.4f}")
        print(f"✓ Checkpoint saved at epoch {epoch}")

logger.info("Training completed successfully")
print("=" * 50)
print("Final Results")
print("=" * 50)
print(f"Final loss: {avg_loss:.4f}")
print(f"Total epochs: 100")
print("=" * 50)

run.finish()
```

**Output in logs.txt**:
```
2026-01-15 10:00:00 - __main__ - INFO - Initializing model...
==================================================
Training Configuration
==================================================
Model: ResNet50
Epochs: 100
Batch size: 32
==================================================
2026-01-15 10:00:05 - __main__ - INFO - Starting training...
Epochs: 100%|██████████| 100/100 [10:00<00:00, 6.00s/it]
2026-01-15 10:00:15 - __main__ - INFO - Epoch 0/100, loss=0.5234
✓ Checkpoint saved at epoch 0
2026-01-15 10:01:15 - __main__ - INFO - Epoch 10/100, loss=0.3456
✓ Checkpoint saved at epoch 10
...
2026-01-15 10:10:00 - __main__ - INFO - Training completed successfully
==================================================
Final Results
==================================================
Final loss: 0.0123
Total epochs: 100
==================================================
```

---

## Best Practices

!!! tip "Tip: Use Smart Mode"
    
    Always use `tqdm_mode="smart"` for clean, readable logs:
    
    ```python
    run = rn.init(project="demo", capture_console=True, tqdm_mode="smart")
    ```

!!! tip "Tip: Combine with Python Logging"
    
    Use Python's logging module for structured logs:
    
    ```python
    logger = logging.getLogger(__name__)
    logger.addHandler(run.get_logging_handler())
    
    logger.info("Training started")  # Structured
    print("Debug info")              # Unstructured
    ```

!!! warning "Performance Note"
    
    Console capture has minimal overhead (~1-2% CPU), but if you're logging thousands of lines per second, consider:
    
    - Using `capture_console=False` and only `get_logging_handler()`
    - Reducing log frequency
    - Using `run.log_text()` for important messages only

---

## Troubleshooting

### Logs not captured?

**Check if console capture is enabled**:
```python
run = rn.init(project="demo", capture_console=True)  # Must be True
```

### Too many tqdm updates in logs?

**Use smart mode**:
```python
run = rn.init(project="demo", capture_console=True, tqdm_mode="smart")
```

### Logger not working?

**Check handler is added**:
```python
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler())  # Don't forget this
logger.setLevel(logging.INFO)  # Set appropriate level
```

### Logs file too large?

**Reduce logging frequency**:
```python
# Instead of logging every step
if step % 100 == 0:  # Log every 100 steps
    logger.info(f"Step {step}, loss={loss}")
```

---

## Migration from v0.5.x

If you're upgrading from v0.5.x, here's how to migrate:

**Before (v0.5.x)**:
```python
import runicorn as rn

run = rn.init(project="demo")

# Manual logging
with open("training.log", "w") as f:
    f.write("Training started\n")
    
run.finish()
```

**After (v0.6.0)**:
```python
import runicorn as rn

# Enable console capture
run = rn.init(project="demo", capture_console=True)

# Automatic logging
print("Training started")  # Automatically captured

run.finish()
# logs.txt is created automatically
```

---

## Next Steps

- [Python SDK Overview](../sdk/overview.md) - Learn all SDK functions
- [Assets System Guide](assets-system.md) - Learn about workspace snapshots
- [FAQ](../reference/faq.md) - Common questions

---

<div align="center">
  <p><a href="../sdk/overview.md">Back to SDK Overview →</a></p>
</div>
