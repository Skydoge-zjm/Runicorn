[English](logging_api.md) | [简体中文](../zh/logging_api.md)

---

# Enhanced Logging API Reference

> **Version**: v0.6.0  
> **Last Updated**: 2025-01-XX  
> **Module**: `runicorn.console`, `runicorn.log_compat`

---

## 📖 Table of Contents

- [Overview](#overview)
- [SDK Parameters](#sdk-parameters)
- [Logging Handler](#logging-handler)
- [MetricLogger Compatibility](#metriclogger-compatibility)
- [Log File Format](#log-file-format)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

Runicorn v0.6.0 introduces an enhanced logging system that provides:

- **Console Capture**: Automatically capture `stdout`/`stderr` to log files
- **Python Logging Integration**: Standard `logging.Handler` for seamless integration
- **MetricLogger Compatibility**: Drop-in replacement for torchvision's MetricLogger
- **Smart tqdm Handling**: Intelligent filtering of progress bar output

### Key Components

| Component | Module | Description |
|-----------|--------|-------------|
| `ConsoleCapture` | `runicorn.console` | Captures stdout/stderr to log file |
| `RunicornLoggingHandler` | `runicorn.console` | Python logging handler |
| `LogManager` | `runicorn.console` | Thread-safe log file manager |
| `MetricLogger` | `runicorn.log_compat.torchvision` | torchvision-compatible logger |

---

## SDK Parameters

### `runicorn.init()` Logging Parameters

```python
import runicorn

run = runicorn.init(
    path="my/experiment",
    capture_console=True,    # Enable console capture
    tqdm_mode="smart",       # tqdm handling mode
)
```

#### `capture_console: bool = False`

When enabled, captures all `stdout` and `stderr` output to the run's `logs.txt` file.

**Features**:
- Output goes to both terminal AND log file (tee behavior)
- Thread-safe writing via `LogManager`
- Immediate flush for real-time WebSocket streaming
- Graceful degradation if capture fails

**Example**:
```python
import runicorn

run = runicorn.init(path="training/resnet", capture_console=True)

# All print statements are captured
print("Starting training...")  # Goes to terminal AND logs.txt
print(f"Epoch 1/100")

run.finish()
```

#### `tqdm_mode: str = "smart"`

Controls how tqdm progress bars are handled during console capture.

| Mode | Behavior |
|------|----------|
| `"smart"` | Captures only final tqdm output, filters intermediate updates |
| `"all"` | Captures all tqdm output (may produce verbose logs) |
| `"none"` | Filters out all tqdm output from logs |

**Example**:
```python
from tqdm import tqdm
import runicorn

# Smart mode (default): only final progress captured
run = runicorn.init(path="exp", capture_console=True, tqdm_mode="smart")

for i in tqdm(range(100)):
    pass  # Progress bar updates filtered, final line captured

run.finish()
```

---

## Logging Handler

### `run.get_logging_handler()`

Returns a Python `logging.Handler` that writes log records to the run's log file.

```python
def get_logging_handler(
    self,
    level: int = logging.INFO,
    fmt: Optional[str] = None,
) -> RunicornLoggingHandler
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `int` | `logging.INFO` | Minimum log level to capture |
| `fmt` | `str \| None` | `None` | Custom format string (uses default if None) |

#### Default Format

```
%(asctime)s | %(levelname)s | %(name)s | %(message)s
```

With `datefmt='%H:%M:%S'`, producing output like:
```
14:30:45 | INFO | my_module | Training started
```

#### Example Usage

```python
import logging
import runicorn

# Initialize run
run = runicorn.init(path="training/bert", capture_console=True)

# Get logger and add Runicorn handler
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(run.get_logging_handler(level=logging.DEBUG))

# Log messages go to logs.txt
logger.info("Model initialized")
logger.debug("Batch size: 32")
logger.warning("GPU memory low")

run.finish()
```

#### Custom Format

```python
handler = run.get_logging_handler(
    level=logging.INFO,
    fmt="[%(levelname)s] %(message)s"
)
logger.addHandler(handler)

logger.info("Custom format")  # Output: [INFO] Custom format
```

### `RunicornLoggingHandler` Class

For advanced use cases, you can instantiate the handler directly:

```python
from runicorn.console import RunicornLoggingHandler

# With explicit run
handler = RunicornLoggingHandler(run=my_run, level=logging.DEBUG)

# Without run (uses active run if available)
handler = RunicornLoggingHandler()
```

#### Features

- **Thread-safe**: Uses `LogManager` for concurrent writes
- **Lazy initialization**: Works even without active Run
- **Auto-cleanup**: Properly releases resources on close

---

## MetricLogger Compatibility

### Overview

`MetricLogger` provides a drop-in replacement for torchvision's `MetricLogger` class, with automatic Runicorn integration.

```python
# Replace this:
# from torchvision.references.detection.utils import MetricLogger

# With this:
from runicorn.log_compat.torchvision import MetricLogger
```

### Basic Usage

```python
from runicorn.log_compat.torchvision import MetricLogger
import runicorn

run = runicorn.init(path="detection/yolo")

metric_logger = MetricLogger(delimiter="  ")

for epoch in range(10):
    for batch in metric_logger.log_every(dataloader, print_freq=10, header=f"Epoch {epoch}"):
        loss = model(batch)
        
        # Metrics automatically logged to Runicorn
        metric_logger.update(loss=loss.item(), lr=optimizer.param_groups[0]['lr'])

run.finish()
```

### API Reference

#### `MetricLogger(delimiter: str = "\t")`

Creates a new MetricLogger instance.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delimiter` | `str` | `"\t"` | Separator between metrics in string output |

#### `MetricLogger.update(**kwargs)`

Update metrics and automatically log to Runicorn.

```python
metric_logger.update(
    loss=0.5,
    accuracy=0.95,
    lr=0.001
)
```

**Supported value types**:
- `float`
- `int`
- `torch.Tensor` (automatically calls `.item()`)

#### `MetricLogger.log_every(iterable, print_freq, header=None)`

Generator that yields items and prints progress.

```python
for data in metric_logger.log_every(dataloader, 10, header="Train"):
    # Process data
    pass
```

**Output format**:
```
Train [  0/100]  eta: 0:05:00  loss: 0.5000 (0.5000)  time: 0.3000  data: 0.1000
Train [ 10/100]  eta: 0:04:30  loss: 0.4500 (0.4750)  time: 0.2800  data: 0.0900
...
Train Total time: 0:05:00 (0.3000 s / it)
```

#### `MetricLogger.synchronize_between_processes()`

Synchronize metrics across distributed training processes.

```python
# After each epoch in distributed training
metric_logger.synchronize_between_processes()
```

### SmoothedValue Class

`SmoothedValue` tracks a series of values with smoothing:

```python
from runicorn.log_compat.torchvision import SmoothedValue

sv = SmoothedValue(window_size=20, fmt="{median:.4f} ({global_avg:.4f})")
sv.update(0.5)
sv.update(0.4)

print(sv.median)      # Median of last 20 values
print(sv.avg)         # Mean of last 20 values
print(sv.global_avg)  # Global average
print(sv.max)         # Maximum in window
print(sv.value)       # Most recent value
```

---

## Log File Format

### Location

Log files are stored at:
```
<storage_root>/runs/<path>/<run_id>/logs.txt
```

### Format

Plain text with timestamps:
```
14:30:45 | Starting training...
14:30:46 | Epoch 1/100
14:30:47 | INFO | trainer | Batch 0: loss=0.5432
14:31:00 | Epoch 1 complete: loss=0.4321, accuracy=0.8765
```

### Real-time Streaming

Log files support real-time streaming via WebSocket:
```
WS ws://127.0.0.1:23300/api/runs/{run_id}/logs/ws
```

The `LogManager` ensures immediate flush after each write for real-time updates.

---

## Examples

### Complete Training Script

```python
import logging
import runicorn
from runicorn.log_compat.torchvision import MetricLogger
from tqdm import tqdm

# Initialize with console capture
run = runicorn.init(
    path="vision/resnet50",
    capture_console=True,
    tqdm_mode="smart"
)

# Setup Python logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(run.get_logging_handler())

# Training loop with MetricLogger
metric_logger = MetricLogger(delimiter="  ")

logger.info("Starting training")
print(f"Config: epochs=100, batch_size=32")

for epoch in range(100):
    for batch in metric_logger.log_every(train_loader, 50, header=f"Epoch {epoch}"):
        loss = train_step(batch)
        metric_logger.update(loss=loss)
    
    # Validation
    val_loss, val_acc = validate(model, val_loader)
    logger.info(f"Epoch {epoch}: val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")
    
    # Log to Runicorn metrics
    run.log({"val_loss": val_loss, "val_acc": val_acc}, step=epoch)

logger.info("Training complete")
run.finish()
```

### Migrating from torchvision

**Before** (torchvision):
```python
from torchvision.references.detection.utils import MetricLogger, SmoothedValue

metric_logger = MetricLogger(delimiter="  ")
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())
```

**After** (Runicorn):
```python
from runicorn.log_compat.torchvision import MetricLogger, SmoothedValue
import runicorn

run = runicorn.init(path="detection/exp1")

metric_logger = MetricLogger(delimiter="  ")
for data in metric_logger.log_every(loader, 10):
    loss = model(data)
    metric_logger.update(loss=loss.item())  # Auto-logged to Runicorn!

run.finish()
```

### Multiple Loggers

```python
import logging
import runicorn

run = runicorn.init(path="exp", capture_console=True)

# Different loggers for different modules
train_logger = logging.getLogger("trainer")
eval_logger = logging.getLogger("evaluator")

# Both use the same Runicorn handler
handler = run.get_logging_handler()
train_logger.addHandler(handler)
eval_logger.addHandler(handler)

train_logger.info("Training started")
eval_logger.info("Evaluation started")

run.finish()
```

---

## Troubleshooting

### Console capture not working

**Symptom**: `print()` output not appearing in `logs.txt`

**Solutions**:
1. Ensure `capture_console=True` is set in `runicorn.init()`
2. Check for errors during initialization (warnings are logged)
3. Verify the run directory exists and is writable

### tqdm output too verbose

**Symptom**: Log file filled with progress bar updates

**Solution**: Use `tqdm_mode="smart"` or `tqdm_mode="none"`:
```python
run = runicorn.init(path="exp", capture_console=True, tqdm_mode="none")
```

### Logging handler not capturing

**Symptom**: `logger.info()` not appearing in logs

**Solutions**:
1. Ensure handler is added: `logger.addHandler(run.get_logging_handler())`
2. Check logger level: `logger.setLevel(logging.DEBUG)`
3. Check handler level matches your log level

### MetricLogger not logging to Runicorn

**Symptom**: Metrics not appearing in Runicorn UI

**Solutions**:
1. Ensure `runicorn.init()` is called before creating MetricLogger
2. Verify an active run exists: `runicorn.get_active_run()` should return a Run
3. Check that values are numeric (float/int/Tensor)

---

## Related Documentation

- **[Runs API](./runs_api.md)** - Experiment management
- **[Metrics API](./metrics_api.md)** - Metrics and real-time logs
- **[Quick Reference](./QUICK_REFERENCE.md)** - API quick reference

---

**Author**: Runicorn Development Team  
**Version**: v0.6.0  
**Last Updated**: 2025-01-XX

**[Back to API Index](API_INDEX.md)**
