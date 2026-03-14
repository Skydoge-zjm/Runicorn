# Integrations

Runicorn is designed to fit into training code that already has its own logging habits. In many cases, migration is mostly about changing one import line and adding `rn.init(...)`.

---

## Python logging { #sdk-python-logging }

If your project already uses the standard `logging` module, attach Runicorn's handler:

<div class="rn-sig" markdown>

**Signature**:
```python
def get_logging_handler(
    level: int = logging.INFO,
    fmt: str | None = None,
) -> logging.Handler
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `level` | `int` | Yes | `logging.INFO` | Usually |
| `fmt` | `str \| None` | Yes | `None` | Situational |

### Parameter notes

- `level`: Minimum log level that should flow into Runicorn through the handler.
- `fmt`: Optional format string if you do not want to rely on the logger's surrounding configuration.

```python
import logging
import runicorn as rn

run = rn.init(path="demo")

logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler())
logger.setLevel(logging.INFO)

logger.info("training started")
logger.warning("loss spike detected")
```

Use this when you want:

- structured logs
- existing logger hierarchy to keep working
- messages to appear in Runicorn without switching to `print()`

---

## Console capture { #sdk-console-capture }

If your code already prints progress information, console capture is often the simplest integration:

```python
run = rn.init(
    path="demo",
    capture_console=True,
    tqdm_mode="smart",
)
```

### `tqdm_mode`

| Value | Meaning |
|-------|---------|
| `smart` | keep useful tqdm output without spamming every update |
| `all` | keep every tqdm update |
| `none` | ignore tqdm output |

For most users, `smart` is the best choice.

---

## torchvision `MetricLogger`

If your training code already uses the torchvision-style metric logger, switch the import:

<div class="rn-sig" markdown>

**Key calls**:
```python
metric_logger = MetricLogger(delimiter: str = "\t")
metric_logger.update(**kwargs) -> None
metric_logger.log_every(iterable, print_freq: int, header: str | None = None)
```
</div>

```python
from runicorn.log_compat.torchvision import MetricLogger

metric_logger = MetricLogger(delimiter="  ")
for batch in metric_logger.log_every(dataloader, 10, header="Train"):
    loss = train_step(batch)
    metric_logger.update(loss=loss, acc=0.9)
```

With an active Runicorn run, `update()` writes through to the run automatically.

---

## ImageNet-style meters

The ImageNet example style is also supported:

<div class="rn-sig" markdown>

**Key calls**:
```python
AverageMeter(name, use_accel=False, fmt=":f", summary_type=Summary.AVERAGE)
AverageMeter.update(val, n: int = 1) -> None
ProgressMeter(num_batches, meters, prefix: str = "")
ProgressMeter.display(batch: int) -> None
```
</div>

```python
from runicorn.log_compat.imagenet import AverageMeter, ProgressMeter

batch_time = AverageMeter("Time", ":6.3f")
losses = AverageMeter("Loss", ":.4e")
top1 = AverageMeter("Acc@1", ":6.2f")
progress = ProgressMeter(100, [batch_time, losses, top1], prefix="Train: ")
```

Calling `progress.display(...)` prints the usual line and also routes current values into the active Runicorn run.

---

## TensorBoard `SummaryWriter`

If your project already writes TensorBoard scalars, text, or hparams, use:

<div class="rn-sig" markdown>

**Key calls**:
```python
SummaryWriter(log_dir=None, comment="", purge_step=None, max_queue=10, flush_secs=120, filename_suffix="")
writer.add_scalar(tag, scalar_value, global_step=None, walltime=None, new_style=False, double_precision=False)
writer.add_scalars(main_tag, tag_scalar_dict, global_step=None, walltime=None)
writer.add_text(tag, text_string, global_step=None, walltime=None)
writer.add_hparams(hparam_dict, metric_dict, run_name=None, global_step=None)
```
</div>

```python
from runicorn.log_compat.tensorboard import SummaryWriter

with SummaryWriter(log_dir="runs/demo") as writer:
    writer.add_scalar("train/loss", 0.25, 7)
    writer.add_scalars("train", {"acc": 0.91, "lr": 0.001}, 7)
    writer.add_text("notes", "warmup finished")
    writer.add_hparams({"lr": 1e-3}, {"hparam/accuracy": 0.94}, global_step=7)
```

These calls write into the active Runicorn run while preserving the familiar TensorBoard calling style.

---

## `tensorboardX` `SummaryWriter`

If your project uses `tensorboardX`, switch to:

<div class="rn-sig" markdown>

**Key calls**:
```python
SummaryWriter(logdir=None, comment="", purge_step=None, max_queue=10, flush_secs=120, filename_suffix="", log_dir=None, **kwargs)
writer.add_scalar(tag, scalar_value, global_step=None, walltime=None, display_name="", summary_description="")
writer.add_text(tag, text_string, global_step=None, walltime=None)
writer.add_hparams(hparam_dict, metric_dict, name=None, global_step=None)
```
</div>

```python
from runicorn.log_compat.tensorboardX import SummaryWriter

with SummaryWriter(logdir="runs/demo") as writer:
    writer.add_scalar("train/loss", 0.2, 3, display_name="loss")
    writer.add_text("notes", "compat text")
    writer.add_hparams(
        {"lr": 0.001, "batch_size": 16},
        {"hparam/accuracy": 0.94, "hparam/loss": 0.08},
        global_step=3,
    )
```

Runicorn 0.7.0 supports the common `tensorboardX` constructor and method shape closely enough for low-friction migration.

---

## Important rule: there must be an active run

All compatibility helpers route data into Runicorn only when an active run exists:

```python
import runicorn as rn

run = rn.init(path="demo")
```

Without an active run, the compatibility layer has nowhere to attach the metrics.

---

## Migration patterns

### Pattern 1: add Runicorn around existing logging

```python
import runicorn as rn
from runicorn.log_compat.tensorboard import SummaryWriter

with rn.init(path="exp/demo") as run:
    writer = SummaryWriter()
    writer.add_scalar("train/loss", 0.3, 1)
```

### Pattern 2: keep your logger, add one handler

```python
with rn.init(path="exp/demo") as run:
    logger.addHandler(run.get_logging_handler())
```

### Pattern 3: let `print()` keep working

```python
with rn.init(path="exp/demo", capture_console=True) as run:
    print("epoch 1 complete")
```

---

## Choosing the right integration

| Existing pattern | Best Runicorn integration |
|------------------|---------------------------|
| many `print()` calls | `capture_console=True` |
| standard `logging` module | `run.get_logging_handler()` |
| torchvision references style | `runicorn.log_compat.torchvision` |
| PyTorch ImageNet example style | `runicorn.log_compat.imagenet` |
| TensorBoard-like scalar logging | `runicorn.log_compat.tensorboard` |
| tensorboardX-based code | `runicorn.log_compat.tensorboardX` |

---

## Next steps

- [Logging Compatibility](../getting-started/logging-compat.md)
- [Run Lifecycle](run-lifecycle.md)
- [Quick Start](../getting-started/quickstart.md)
