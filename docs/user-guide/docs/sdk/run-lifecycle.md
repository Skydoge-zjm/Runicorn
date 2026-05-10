# Run Lifecycle

This page covers the part of the SDK that every Runicorn user should understand well: creating a run, logging metrics, recording summaries, and finishing cleanly.

---

## `rn.init(...)` { #sdk-init }

Create a new run:

<div class="rn-sig" markdown>

**Signature**:
```python
def init(
    path: str | None = None,
    storage: str | None = None,
    run_id: str | None = None,
    alias: str | None = None,
    capture_env: bool = False,
    snapshot_code: bool = False,
    workspace_root: str | None = None,
    snapshot_format: str = "zip",
    force_snapshot: bool = False,
    capture_console: bool = False,
    tqdm_mode: str = "smart",
) -> Run | NoOpRun
```
</div>

```python
import runicorn as rn

run = rn.init(
    path="cv/resnet50/baseline",
    storage="E:\\RunicornData",
    alias="trial-01",
    capture_env=False,
    snapshot_code=False,
    workspace_root=None,
    snapshot_format="zip",
    force_snapshot=False,
    capture_console=False,
    tqdm_mode="smart",
)
```


| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `path` | `str \| None` | Yes | `None` | Yes |
| `storage` | `str \| None` | Yes | `None` | Situational |
| `run_id` | `str \| None` | Yes | auto-generated | No |
| `alias` | `str \| None` | Yes | `None` | Usually |
| `capture_env` | `bool` | Yes | `False` | Situational |
| `snapshot_code` | `bool` | Yes | `False` | Usually |
| `workspace_root` | `str \| None` | Yes | `None` | Situational |
| `snapshot_format` | `str` | Yes | `"zip"` | No |
| `force_snapshot` | `bool` | Yes | `False` | Rarely |
| `capture_console` | `bool` | Yes | `False` | Usually |
| `tqdm_mode` | `str` | Yes | `"smart"` | Yes when using console capture |

### Parameter notes

- `path`: Hierarchical run path such as `cv/resnet50/baseline`. `None` becomes `"default"`.
- `storage`: Override the resolved storage root for this run only.
- `run_id`: Explicit run ID. Mostly useful for controlled imports, tests, or special recovery flows.
- `alias`: Short human-friendly label shown in the UI.
- `capture_env`: Capture environment information such as runtime and system context.
- `snapshot_code`: Archive the workspace at run start so the run records the code state it used.
- `workspace_root`: Explicit root directory for code snapshotting and output scanning.
- `snapshot_format`: Snapshot archive format. Currently only `"zip"` is supported.
- `force_snapshot`: Override snapshot size or file-count safety checks for unusually large workspaces.
- `capture_console`: Capture stdout/stderr into `logs.txt` so logs appear in the viewer even if you use `print()`.
- `tqdm_mode`: Controls tqdm handling: `smart`, `all`, or `none`.

### Path rules

`path` is normalized and validated:

- `None` becomes `"default"`
- `"/"` becomes the root path
- backslashes are normalized to `/`
- invalid characters and traversal-like values are rejected

Examples:

```python
rn.init(path="cv/detection/yolo")
rn.init(path="research/ablation/seed-42")
rn.init(path="/")  # root-level runs
```

---

## `run.log(...)` { #sdk-log }

Log scalar metrics during training:

<div class="rn-sig" markdown>

**Signature**:
```python
def log(
    data: dict | None = None,
    *,
    step: int | None = None,
    stage: str | None = None,
    **kwargs,
) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `data` | `dict \| None` | Yes | `None` | Usually |
| `step` | `int \| None` | Yes | auto-increment | Situational |
| `stage` | `str \| None` | Yes | `None` | Situational |
| `**kwargs` | extra scalar fields | Yes | none | Situational |

### Parameter notes

- `data`: Main metric payload as a dict, such as `{"loss": 0.42, "acc": 0.88}`.
- `step`: Explicit step value. If omitted, Runicorn increments the internal `global_step`.
- `stage`: Optional stage label. In many projects, a common pattern is values like `"epoch_1"`, `"epoch_2"`, and so on.
- `**kwargs`: Additional metrics. Useful when you prefer `run.log(loss=..., acc=...)`.

```python
run.log({"loss": 0.42, "acc": 0.88}, stage="epoch_1")
run.log(val_loss=0.39, val_acc=0.90, stage="epoch_2")
```

### What `run.log()` does

- accepts either a dict, keyword metrics, or both
- records a `global_step`
- records a `time` field automatically
- optionally records `stage`

### Step behavior

If you do not pass `step`, Runicorn auto-increments an internal global step counter:

```python
run.log({"loss": 0.5})  # global_step = 1
run.log({"loss": 0.4})  # global_step = 2
```

If you do pass `step`, Runicorn uses that explicit value. Most users do not need that in everyday training loops, so the examples in this guide stick to auto-incremented steps.

### Stage behavior

Use `stage` when you want the UI to separate metric records into coarse buckets. In many training scripts, people simply use epoch-style labels:

```python
run.log({"loss": 0.8}, stage="epoch_1")
run.log({"loss": 0.4}, stage="epoch_2")
run.log({"val_loss": 0.35}, stage="epoch_3")
```

### How to handle train vs eval without step misalignment

In practice, many users do **not** rely on `stage` alone to distinguish train and eval. A clearer pattern is:

- use different metric names such as `train_loss`, `train_acc`, `val_loss`, `val_acc`
- keep train and eval aligned to the same training step or epoch boundary
- avoid bumping `step` by one just because you entered evaluation

For example, if you evaluate once per epoch or every 10,000 steps, it is usually better to treat that eval result as belonging to the same step boundary you just finished, instead of logging it at `step + 1`.

One practical pattern is to keep the latest eval value on the training timeline:

```python
last_val_acc = 0.0

for step in range(1, total_steps + 1):
    train_loss, train_acc = train_step()

    if step % 10000 == 0:
        last_val_acc = evaluate()

    run.log({
        "train_loss": train_loss,
        "train_acc": train_acc,
        "val_acc": last_val_acc,
    }, stage=f"epoch_{current_epoch}")
```

Why people do this:

- train and eval metrics stay on the same step axis
- the chart remains aligned at epoch or evaluation boundaries
- you avoid the visual offset caused by logging eval at `step + 1`

If your team prefers it, using an initial placeholder such as `val_acc = 0.0` until the first eval finishes is a valid pragmatic choice for alignment-focused charts.

---

## `run.set_primary_metric(...)` { #sdk-primary-metric }

Tell Runicorn which metric should be treated as the main score:

<div class="rn-sig" markdown>

**Signature**:
```python
def set_primary_metric(metric_name: str, mode: str = "max") -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `metric_name` | `str` | No | none | Yes |
| `mode` | `str` | Yes | `"max"` | Yes |

### Parameter notes

- `metric_name`: The metric to surface in the experiments table and compare flows.
- `mode`: Use `"max"` when higher is better, `"min"` when lower is better.

```python
run.set_primary_metric("val_acc", mode="max")
```

Or for loss:

```python
run.set_primary_metric("val_loss", mode="min")
```

The best value is tracked as you log metrics and written into the summary on finish.

---

## `run.log_text(...)` { #sdk-log-text }

Write text lines into the run log:

<div class="rn-sig" markdown>

**Signature**:
```python
def log_text(text: str) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `text` | `str` | No | none | Situational |

### Parameter notes

- `text`: Free-form log text. Multi-line strings are supported and timestamps are prepended to non-empty lines.

```python
run.log_text("starting epoch 3")
run.log_text("checkpoint saved")
```

`run.log_text(...)` writes directly to the run's `logs.txt`.

Important behavior:

- it **does write** to `logs.txt`
- it **does not automatically print** to your terminal
- if you want both terminal output and Runicorn logging, call both `print(...)` and `run.log_text(...)`, or enable `capture_console=True`

Runicorn prepends timestamps to non-empty lines before writing them.

### `run.log_text(...)` vs `print(...)` when `capture_console=True`

| Call | Terminal output | `logs.txt` | Typical use |
|------|------------------|------------|-------------|
| `print(...)` | Yes | Yes | Console-first progress messages that you also want captured |
| `run.log_text(...)` | No | Yes | Explicit Runicorn log entries even when you do not want terminal output |

This is helpful when:

- you want explicit, Runicorn-owned log entries
- you want short checkpoint/progress notes
- you want messages to appear in the logs tab even without console capture

### Where to view the recorded text

In the Web UI, open the run detail page and switch to the **Logs** tab. That tab reads the run log stream from `logs.txt`, so `run.log_text(...)` entries appear there alongside other captured log output.

---

## `run.summary(...)` { #sdk-summary }

Store run-level summary data.

Use it for the final result or current overall state of a run, not for per-step history.

<div class="rn-sig" markdown>

**Signature**:
```python
def summary(update: dict) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `update` | `dict` | No | none | Yes |

### Parameter notes

- `update`: Summary fields to merge into `summary.json`, such as final scores, notes, selected checkpoints, or any metadata you want surfaced at the run level.

Typical example:

```python
run.summary({
    "final_acc": 0.91,
    "best_epoch": 8,
    "notes": "best seed so far",
})
```

Most users call `run.summary(...)` near the end of training, after an important evaluation, or whenever they want to update a run-level field such as `best_ckpt`, `notes`, or `final_acc`.

Summary updates merge into the existing summary file, so multiple calls are fine:

```python
run.summary({"final_acc": 0.91})
run.summary({"notes": "best seed so far"})
```

Use `run.log(...)` for timeline data and `run.summary(...)` for run-level conclusions.

In the Web UI, summary fields appear in the run detail page as run-level metadata.

---

## `run.finish(...)` { #sdk-finish }

Finish the run explicitly:

<div class="rn-sig" markdown>

**Signature**:
```python
def finish(status: str = "finished") -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `status` | `str` | Yes | `"finished"` | Yes |

### Parameter notes

- `status`: Final run status. In practice, use `finished`, `failed`, or `interrupted`.

```python
# Most common
run.finish()

# Explicit status
run.finish(status="finished")
```

### What happens if you omit the parameter

If you call `run.finish()` without arguments, Runicorn uses the default status:

- `finished`

So in normal scripts, omitting the parameter is completely fine.

### When status is chosen automatically

There are two important automatic cases:

- if you use `with rn.init(...) as run:`, Runicorn marks the run as `finished` on normal exit and `failed` if the block raises an exception
- if a run is still marked as `running` but the process later disappears unexpectedly, the viewer's background status checker can mark it as `failed`

### When status is **not** inferred automatically

If you call `run.finish(...)` yourself, Runicorn does **not** inspect your training state and guess whether the run was successful. It uses:

- the explicit `status` you passed, or
- `finished` if you passed nothing

Recommended final statuses when calling it yourself:

- `finished`
- `failed`
- `interrupted`

In 0.7.0, finish behavior is safer than older versions:

- post-finish writes are blocked
- output watchers are stopped
- best-metric summary fields are flushed
- status is normalized to valid stored values

---

## Context manager style

This is a common and safer pattern when you want automatic cleanup:

```python
import runicorn as rn

with rn.init(path="training/safe") as run:
    run.log({"loss": 0.1})
```

Benefits:

- success exits become `finished`
- exceptions become `failed`
- you are less likely to forget cleanup

---

## Disable tracking without changing code shape

```python
import runicorn as rn

rn.set_enabled(False)
run = rn.init(path="debug")
run.log({"loss": 0.1})   # no-op
run.finish()             # no-op
```

This returns a no-op run object, which is useful for inference scripts, debugging, or temporarily disabling tracking in shared code.

---

## Full lifecycle example

```python
import math
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image, ImageDraw
import runicorn as rn

run = rn.init(
    path="cv/resnet50/baseline",
    alias="seed-42",
    capture_console=True,
)

model = nn.Sequential(
    nn.Linear(128, 64),
    nn.ReLU(),
    nn.Linear(64, 10),
)
optimizer = optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()

run.set_primary_metric("val_acc", mode="max")
run.log_config(extra={"optimizer": "adam", "lr": 1e-3, "epochs": 3})

latest_val_acc = 0.0

for epoch in range(1, 4):
    model.train()
    epoch_acc_sum = 0.0
    epoch_steps = 0

    dataloader = [
        (torch.randn(32, 128), torch.randint(0, 10, (32,)))
        for _ in range(5)
    ]

    for batch_idx, (inputs, targets) in enumerate(dataloader, start=1):
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        curve_step = (epoch - 1) * len(dataloader) + batch_idx
        simulated_train_loss = 1.6 * math.exp(-0.18 * curve_step) + 0.04 * torch.rand(1).item()
        batch_acc = min(0.95, 0.35 + 0.08 * math.log1p(curve_step) + 0.02 * torch.rand(1).item())
        epoch_acc_sum += batch_acc
        epoch_steps += 1
        
        print(f"train_loss: {simulated_train_loss:.4f}")

        run.log({
            "train_loss": simulated_train_loss,
            "train_acc": batch_acc,
            "val_acc": latest_val_acc,
        }, stage=f"epoch_{epoch}")

    train_acc = epoch_acc_sum / epoch_steps
    latest_val_acc = 0.70 + 0.05 * epoch

    preview = Image.new("RGB", (320, 160), "white")
    draw = ImageDraw.Draw(preview)
    draw.rounded_rectangle((10, 10, 310, 150), radius=12, outline="navy", width=3)
    draw.text((24, 28), f"Epoch {epoch}", fill="black")
    draw.text((24, 68), f"train_acc={train_acc:.3f}", fill="green")
    draw.text((24, 102), f"val_acc={latest_val_acc:.3f}", fill="purple")
    run.log_image(
        "epoch_preview",
        preview,
        caption=f"Metrics snapshot for epoch {epoch}",
    )

run.summary({
    "epochs": 3,
    "final_train_acc": train_acc,
    "final_val_acc": latest_val_acc,
    "final_note": "baseline complete",
})

run.finish()
```

In this pattern, `step` is auto-incremented by Runicorn, and `val_acc` is carried as the latest known evaluation value. That keeps train and validation metrics on one aligned step axis instead of introducing a separate extra step just for evaluation.

---

## Next steps

- [Assets & Outputs](assets-and-outputs.md)
- [Integrations](integrations.md)
- [Quick Start](../getting-started/quickstart.md)
