[English](ENHANCED_LOGGING_GUIDE.md) | [简体中文](../zh/ENHANCED_LOGGING_GUIDE.md)

---

# Enhanced Logging Guide

> **Version**: v0.6.0  
> **Feature**: Console Capture, Python Logging Integration, MetricLogger Compatibility

---

## 📋 Overview

Runicorn v0.6.0 introduces an **Enhanced Logging System** that automatically captures console output without requiring code changes. This system provides:

- **Console Capture**: Automatically capture `print()` and `sys.stderr` output to `logs.txt`
- **Python Logging Integration**: Seamlessly integrate with Python's `logging` module
- **MetricLogger Compatibility**: Drop-in replacement for torchvision-style MetricLogger
- **Smart tqdm Handling**: Intelligent progress bar filtering to prevent log bloat

### Design Philosophy

The Enhanced Logging System separates **text logs** from **structured metrics**:

| Type | User Action | Storage | Purpose |
|------|-------------|---------|---------|
| Text Logs | `print(...)` | `logs.txt` | Debugging, viewing |
| Structured Metrics | `run.log({...})` | Database | Charting, comparison |

This separation ensures:
- `print()` output is captured as-is without forced parsing
- `run.log()` provides explicit, structured metric recording
- Both are valuable and serve different purposes

---

## 🚀 Quick Start

### Basic Console Capture

Enable console capture with a single parameter:

```python
import runicorn as rn

# Enable console capture
run = rn.init(path="my_experiment", capture_console=True)

# All print output is automatically captured
print("Starting training...")
print(f"Epoch 1: loss=0.5, accuracy=0.85")

# Structured metrics for charting
run.log({"loss": 0.5, "accuracy": 0.85})

run.finish()
```

After running, check `logs.txt` in your run directory:
```
[10:30:15] Starting training...
[10:30:16] Epoch 1: loss=0.5, accuracy=0.85
```

### Using Python Logging Handler

Integrate with existing Python loggers:

```python
import logging
import runicorn as rn

run = rn.init(path="my_experiment")

# Get Runicorn logging handler
handler = run.get_logging_handler()

# Add to your logger
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Log messages go to logs.txt
logger.info("Model initialized")
logger.warning("Low GPU memory")

run.finish()
```

### MetricLogger Drop-in Replacement

For projects using torchvision-style MetricLogger, change just one import:

```python
# Before (torchvision style)
# from utils import MetricLogger

# After (Runicorn integration)
from runicorn.log_compat.torchvision import MetricLogger

import runicorn as rn

run = rn.init(path="training", capture_console=True)

metric_logger = MetricLogger(delimiter="  ")

for epoch in range(10):
    for data in metric_logger.log_every(dataloader, 10, header=f"Epoch {epoch}"):
        loss = train_step(data)
        # Automatically logs to both console AND run.log()
        metric_logger.update(loss=loss)

run.finish()
```

---

## 📚 Features

### Console Capture

Console capture redirects `stdout` and `stderr` to both the terminal and a log file using a "Tee" pattern.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `capture_console` | `bool` | `False` | Enable console capture |
| `tqdm_mode` | `str` | `"smart"` | How to handle progress bars |

#### Example

```python
run = rn.init(
    path="experiment",
    capture_console=True,
    tqdm_mode="smart",  # "smart", "all", or "none"
)
```

### tqdm Handling Modes

Progress bars (tqdm, rich.progress) use carriage return (`\r`) for dynamic updates. Without special handling, each update becomes a new line in log files, causing massive bloat.

Runicorn provides three modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `"smart"` | Buffer `\r` lines, only write final version | **Recommended** - Clean logs |
| `"all"` | Write every update (replace `\r` with `\n`) | Debugging progress issues |
| `"none"` | Ignore all lines containing `\r` | Minimal logs |

#### Smart Mode Example

```python
from tqdm import tqdm
import runicorn as rn

run = rn.init(path="training", capture_console=True, tqdm_mode="smart")

# tqdm progress bar
for i in tqdm(range(100), desc="Training"):
    # ... training code ...
    pass

run.finish()
```

**Terminal output** (dynamic):
```
Training: 100%|██████████| 100/100 [00:10<00:00, 10.0it/s]
```

**logs.txt** (clean, only final state):
```
[10:30:15] Training: 100%|██████████| 100/100 [00:10<00:00, 10.0it/s]
```

### Python Logging Handler

`RunicornLoggingHandler` is a standard `logging.Handler` that writes to Runicorn's log file.

#### Features

- Thread-safe via `LogManager`
- Lazy initialization (works even without active Run)
- Configurable log level and format
- Works independently of console capture

#### API

```python
handler = run.get_logging_handler(
    level=logging.INFO,      # Minimum log level
    fmt="%(asctime)s | %(levelname)s | %(message)s"  # Custom format
)
```

#### Example: Multiple Loggers

```python
import logging
import runicorn as rn

run = rn.init(path="experiment")
handler = run.get_logging_handler()

# Add to multiple loggers
for name in ["model", "data", "trainer"]:
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# All logs go to the same logs.txt
logging.getLogger("model").info("Model loaded")
logging.getLogger("data").info("Dataset ready")
logging.getLogger("trainer").info("Training started")

run.finish()
```

### MetricLogger Compatibility

The `MetricLogger` class is a drop-in replacement for torchvision's MetricLogger, widely used in CV projects (DeiT, DETR, DINOv2, BLIP, etc.).

#### Features

- **100% API Compatible**: All methods work identically
- **Automatic Runicorn Integration**: `update()` calls automatically log to `run.log()`
- **Pure Python**: Works with or without PyTorch
- **Distributed Training Support**: `synchronize_between_processes()` works as expected

#### Classes

| Class | Description |
|-------|-------------|
| `MetricLogger` | Main logger with smoothed value tracking |
| `SmoothedValue` | Sliding window statistics (median, avg, global_avg, max) |

#### Example: Training Loop

```python
from runicorn.log_compat.torchvision import MetricLogger
import runicorn as rn

run = rn.init(path="deit_training", capture_console=True)

metric_logger = MetricLogger(delimiter="  ")

for epoch in range(100):
    header = f"Epoch: [{epoch}]"
    
    for samples, targets in metric_logger.log_every(train_loader, 10, header):
        loss = model(samples, targets)
        
        # This automatically:
        # 1. Updates internal SmoothedValue
        # 2. Calls run.log({"loss": loss_value})
        metric_logger.update(loss=loss.item())
        metric_logger.update(lr=optimizer.param_groups[0]["lr"])
    
    # Sync across GPUs (if distributed)
    metric_logger.synchronize_between_processes()

run.finish()
```

---

## 📖 API Reference

### Run Parameters

```python
run = rn.init(
    path="experiment",
    capture_console=True,   # Enable console capture
    tqdm_mode="smart",      # tqdm handling mode
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `capture_console` | `bool` | `False` | Capture stdout/stderr to logs.txt |
| `tqdm_mode` | `str` | `"smart"` | Progress bar handling: "smart", "all", "none" |

### run.get_logging_handler()

```python
handler = run.get_logging_handler(
    level: int = logging.INFO,
    fmt: Optional[str] = None,
) -> logging.Handler
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `int` | `logging.INFO` | Minimum log level |
| `fmt` | `str` | `None` | Custom format string |

**Default format**: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`

### MetricLogger Class

```python
from runicorn.log_compat.torchvision import MetricLogger, SmoothedValue
```

#### MetricLogger

| Method | Description |
|--------|-------------|
| `__init__(delimiter="\t")` | Create logger with specified delimiter |
| `update(**kwargs)` | Update metrics and log to Runicorn |
| `log_every(iterable, print_freq, header)` | Generator with progress printing |
| `add_meter(name, meter)` | Add custom SmoothedValue meter |
| `synchronize_between_processes()` | Sync across distributed processes |

#### SmoothedValue

| Property | Description |
|----------|-------------|
| `median` | Median of values in window |
| `avg` | Mean of values in window |
| `global_avg` | Global average across all updates |
| `max` | Maximum value in window |
| `value` | Most recent value |

---

## 💡 Examples

### Training Script with Console Capture

```python
import runicorn as rn
from tqdm import tqdm

def train():
    run = rn.init(
        path="resnet_training",
        capture_console=True,
        tqdm_mode="smart",
    )
    
    print("=" * 50)
    print("Starting ResNet Training")
    print("=" * 50)
    
    for epoch in range(10):
        print(f"\nEpoch {epoch + 1}/10")
        
        # Training loop with tqdm
        train_loss = 0
        for batch in tqdm(train_loader, desc="Training"):
            loss = train_step(batch)
            train_loss += loss
        
        avg_loss = train_loss / len(train_loader)
        print(f"Train Loss: {avg_loss:.4f}")
        
        # Log structured metrics
        run.log({"epoch": epoch, "train_loss": avg_loss})
    
    print("\nTraining complete!")
    run.finish()

if __name__ == "__main__":
    train()
```

### Integration with Existing Loggers

```python
import logging
import runicorn as rn

# Existing logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my_app")

def train_with_existing_logger():
    run = rn.init(path="experiment")
    
    # Add Runicorn handler to existing logger
    handler = run.get_logging_handler(level=logging.DEBUG)
    logger.addHandler(handler)
    
    logger.info("Starting experiment")
    
    for epoch in range(10):
        loss = train_epoch()
        logger.info(f"Epoch {epoch}: loss={loss:.4f}")
        run.log({"loss": loss})
    
    logger.info("Experiment complete")
    run.finish()
```

### MetricLogger Migration

**Before** (standalone MetricLogger):
```python
from utils import MetricLogger

metric_logger = MetricLogger()
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())
```

**After** (Runicorn integration):
```python
from runicorn.log_compat.torchvision import MetricLogger
import runicorn as rn

run = rn.init(path="training", capture_console=True)

metric_logger = MetricLogger()
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())  # Now also logs to Runicorn!

run.finish()
```

---

## 🔧 Troubleshooting

### Issue: Console output not captured

**Cause**: `capture_console=False` (default)

**Solution**:
```python
run = rn.init(path="experiment", capture_console=True)
```

### Issue: Log file has too many tqdm lines

**Cause**: Using `tqdm_mode="all"`

**Solution**:
```python
run = rn.init(path="experiment", capture_console=True, tqdm_mode="smart")
```

### Issue: Logging handler not writing

**Cause**: Handler created before `run.init()` or after `run.finish()`

**Solution**: Create handler after init, use before finish:
```python
run = rn.init(path="experiment")
handler = run.get_logging_handler()  # Create after init
logger.addHandler(handler)
# ... use logger ...
run.finish()  # Handler stops working after this
```

### Issue: MetricLogger not logging to Runicorn

**Cause**: No active Run when `update()` is called

**Solution**: Ensure `rn.init()` is called before using MetricLogger:
```python
import runicorn as rn
from runicorn.log_compat.torchvision import MetricLogger

run = rn.init(path="experiment")  # Must be called first
metric_logger = MetricLogger()
metric_logger.update(loss=0.5)  # Now logs to Runicorn
run.finish()
```

### Issue: ANSI colors not showing in Web UI

**Cause**: This is expected behavior - ANSI codes are preserved in `logs.txt`

**Solution**: The Web UI's LogsViewer component renders ANSI colors. View logs in the Web UI for colored output.

---

## 📊 Log File Format

Console capture writes to `<run_dir>/logs.txt` with timestamps:

```
[HH:MM:SS] <message>
```

Example:
```
[10:30:15] Starting training...
[10:30:16] Epoch 1/10
[10:30:45] Training: 100%|██████████| 100/100 [00:29<00:00, 3.45it/s]
[10:30:46] Train Loss: 0.4523
[10:31:15] Epoch 2/10
...
```

Python logging handler uses configurable format (default):
```
HH:MM:SS | LEVEL | logger_name | message
```

---

**[Back to Guides](README.md)** | **[Back to Main](../../README.md)**
