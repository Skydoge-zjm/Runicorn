# Logging Compatibility

Runicorn supports both its own logging APIs and several common ML logging patterns that people already use in training scripts.

---

## Core options

### Console capture

```python
run = rn.init(path="demo", capture_console=True, tqdm_mode="smart")
```

This captures `print()` output and writes it to `logs.txt` while still showing it in the terminal.

That is different from `run.log_text(...)`, which writes directly to `logs.txt` but does not print to the terminal by itself.

### Python logging integration

```python
import logging
import runicorn as rn

run = rn.init(path="demo")
logger = logging.getLogger(__name__)
logger.addHandler(run.get_logging_handler())
logger.info("training started")
```

---

## Compatibility matrix

| Pattern | Import to use |
|--------|----------------|
| torchvision MetricLogger | `from runicorn.log_compat.torchvision import MetricLogger` |
| ImageNet AverageMeter | `from runicorn.log_compat.imagenet import AverageMeter, ProgressMeter` |
| TensorBoard SummaryWriter | `from runicorn.log_compat.tensorboard import SummaryWriter` |
| tensorboardX SummaryWriter | `from runicorn.log_compat.tensorboardX import SummaryWriter` |

---

## torchvision MetricLogger

```python
from runicorn.log_compat.torchvision import MetricLogger

metric_logger = MetricLogger(delimiter="  ")
for batch in metric_logger.log_every(dataloader, 10, header="Train"):
    loss = train_step(batch)
    metric_logger.update(loss=loss)
```

When an active Runicorn run exists, updates are routed into Runicorn automatically.

---

## ImageNet-style meters

```python
from runicorn.log_compat.imagenet import AverageMeter, ProgressMeter

losses = AverageMeter("Loss", ":.4f")
top1 = AverageMeter("Acc@1", ":.2f")
progress = ProgressMeter(len(loader), [losses, top1], prefix="Train: ")

for i, batch in enumerate(loader):
    loss, acc = train_step(batch)
    losses.update(loss)
    top1.update(acc)
    if i % 10 == 0:
        progress.display(i)
```

---

## TensorBoard and tensorboardX

```python
from runicorn.log_compat.tensorboard import SummaryWriter

writer = SummaryWriter()
writer.add_scalar("train/loss", 0.42, 1)
writer.add_text("notes", "warmup finished", 1)
writer.add_hparams({"lr": 1e-3}, {"val_acc": 0.88})
```

The tensorboardX-compatible module supports the same migration pattern:

```python
from runicorn.log_compat.tensorboardX import SummaryWriter
```

---

## When automatic routing works

The compatibility helpers write through to Runicorn when there is an active run:

```python
import runicorn as rn

run = rn.init(path="demo")
```

If no active run exists, the compatibility layer cannot attach your metrics to a Runicorn run.

---

## Recommended setup

For most users:

1. start a Runicorn run normally
2. enable `capture_console=True` if you want console logs
3. use the compat import that matches your existing training loop

---

## Next steps

- [SDK Integrations](../sdk/integrations.md)
- [Run Lifecycle](../sdk/run-lifecycle.md)
- [Logs, Assets & Images](../ui/logs-assets-and-images.md)
