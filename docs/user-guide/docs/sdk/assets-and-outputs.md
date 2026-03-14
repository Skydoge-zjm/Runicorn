# Assets & Outputs

Runicorn can track much more than scalar metrics. This page covers the asset-related SDK APIs you are most likely to use in real projects.

---

## What counts as an asset in Runicorn

In everyday use, the following usually end up in the assets UI:

- code snapshots
- images
- config metadata
- dataset references
- pretrained references
- archived outputs such as checkpoints or reports

---

## Code snapshots { #sdk-code-snapshots }

### Automatic snapshot at run start

The simplest workflow:

```python
run = rn.init(
    path="cv/resnet50/baseline",
    snapshot_code=True,
)
```

This captures the workspace into a ZIP archive at init time and records it as a run asset.

Useful parameters:

- `workspace_root`: explicitly control what counts as the workspace
- `force_snapshot=True`: override snapshot size/file-count limits when needed

### Manual snapshot helper

Runicorn also exports `snapshot_workspace` at the top level:

<div class="rn-sig" markdown>

**Signature**:
```python
def snapshot_workspace(
    root: Path,
    out_zip: Path,
    *,
    ignore_file: str = ".rnignore",
    extra_excludes: list[str] | None = None,
    max_total_bytes: int = 500 * 1024 * 1024,
    max_files: int = 200_000,
    force_snapshot: bool = False,
) -> dict
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `root` | `Path` | No | none | Yes |
| `out_zip` | `Path` | No | none | Yes |
| `ignore_file` | `str` | Yes | `".rnignore"` | Usually |
| `extra_excludes` | `list[str] \| None` | Yes | `None` | Situational |
| `max_total_bytes` | `int` | Yes | `500 * 1024 * 1024` | Usually |
| `max_files` | `int` | Yes | `200_000` | Usually |
| `force_snapshot` | `bool` | Yes | `False` | Rarely |

### Parameter notes

- `root`: Workspace root to snapshot.
- `out_zip`: Destination zip path.
- `ignore_file`: Ignore-file name inside the workspace.
- `extra_excludes`: Extra glob-style exclusions for this call only.
- `max_total_bytes` / `max_files`: Safety limits for large workspaces.
- `force_snapshot`: Override those safety limits.

```python
from pathlib import Path
from runicorn import snapshot_workspace

result = snapshot_workspace(
    root=Path("."),
    out_zip=Path("snapshot.zip"),
)
```

Use this when you want manual control instead of tying snapshotting to `rn.init()`.

---

## Images { #sdk-log-image }

Use `run.log_image()` for anything you want to preview visually in the UI:

<div class="rn-sig" markdown>

**Signature**:
```python
def log_image(
    key: str,
    image: Any,
    step: int | None = None,
    caption: str | None = None,
    format: str = "png",
    quality: int = 90,
) -> str
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `key` | `str` | No | none | Yes |
| `image` | `Any` | No | none | Yes |
| `step` | `int \| None` | Yes | `None` | Situational |
| `caption` | `str \| None` | Yes | `None` | Situational |
| `format` | `str` | Yes | `"png"` | Usually |
| `quality` | `int` | Yes | `90` | Situational |

### Parameter notes

- `key`: Logical image name, such as `"prediction"` or `"sample_grid"`.
- `image`: PIL image, NumPy array, raw bytes, or a file path.
- `step`: Optional step for timeline context in the UI.
- `caption`: Optional human-readable caption.
- `format`: Output format used when Runicorn writes the image itself.
- `quality`: Mostly relevant for lossy formats such as JPEG.

```python
run.log_image("prediction", image, step=100, caption="validation sample")
```

Supported input types include:

- PIL images
- NumPy arrays
- raw bytes
- file paths

Typical use cases:

- classification predictions
- segmentation overlays
- diffusion samples
- training diagnostics

---

## Config metadata { #sdk-log-config }

Use `run.log_config()` for structured run metadata that should be easy to browse later:

<div class="rn-sig" markdown>

**Signature**:
```python
def log_config(
    *,
    args: Any = None,
    extra: dict | None = None,
    config_files: list[str | Path] | None = None,
) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `args` | `Any` | Yes | `None` | Situational |
| `extra` | `dict \| None` | Yes | `None` | Usually |
| `config_files` | `list[str \| Path] \| None` | Yes | `None` | Situational |

### Parameter notes

- `args`: Typically an argparse namespace or plain dict.
- `extra`: Arbitrary extra metadata to persist with the run.
- `config_files`: Paths to config files you want associated with the run.

```python
run.log_config(
    args=args,
    extra={"lr": 1e-3, "optimizer": "adamw"},
    config_files=["config.yaml", "augment.yaml"],
)
```

What it is good for:

- argparse namespaces
- handwritten config dicts
- file lists

Runicorn converts many common non-JSON objects into safe forms automatically.

---

## Dataset references { #sdk-log-dataset }

Use `run.log_dataset()` when you want the run to remember which dataset or input directory it used:

<div class="rn-sig" markdown>

**Signature**:
```python
def log_dataset(
    name: str,
    root_or_uri: str | Path | dict,
    *,
    context: str = "train",
    save: bool = False,
    description: str | None = None,
    force_save: bool = False,
    max_archive_bytes: int = 5 * 1024**3,
    max_archive_files: int = 2_000_000,
) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `name` | `str` | No | none | Yes |
| `root_or_uri` | `str \| Path \| dict` | No | none | Yes |
| `context` | `str` | Yes | `"train"` | Usually |
| `save` | `bool` | Yes | `False` | Situational |
| `description` | `str \| None` | Yes | `None` | Situational |
| `force_save` | `bool` | Yes | `False` | Rarely |
| `max_archive_bytes` | `int` | Yes | `5 * 1024**3` | Usually |
| `max_archive_files` | `int` | Yes | `2_000_000` | Usually |

### Parameter notes

- `name`: Dataset label shown in the run.
- `root_or_uri`: Local path or logical dataset identifier.
- `context`: Typical values include `train`, `eval`, `test`, or `config`.
- `save`: Archive the dataset reference target instead of storing metadata only.
- `description`: Free-form explanation of what this dataset entry represents.
- `force_save`: Override size/count checks when archiving.
- `max_archive_bytes` / `max_archive_files`: Safety limits for archive mode.

```python
run.log_dataset(
    "imagenet-train",
    "/data/imagenet/train",
    context="train",
    description="main supervised training set",
)
```

### Metadata-only mode

The default behavior stores metadata and fingerprints when possible, without archiving the dataset itself.

### Archive mode

Set `save=True` if you want the referenced path archived:

```python
run.log_dataset(
    "small-validation-set",
    "./data/val",
    context="eval",
    save=True,
)
```

### Remote or logical dataset identifiers

You can also pass a dict instead of a filesystem path:

```python
run.log_dataset(
    "hf-dataset",
    {"repo": "user/dataset", "split": "train"},
)
```

This is useful for Hugging Face datasets, object stores, or internal dataset registries.

---

## Pretrained references { #sdk-log-pretrained }

Use `run.log_pretrained()` to record the model you started from:

<div class="rn-sig" markdown>

**Signature**:
```python
def log_pretrained(
    name: str,
    *,
    path_or_uri: str | Path | dict | None = None,
    save: bool = False,
    source_type: str = "unknown",
    description: str | None = None,
    force_save: bool = False,
    max_archive_bytes: int = 5 * 1024**3,
    max_archive_files: int = 2_000_000,
) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `name` | `str` | No | none | Yes |
| `path_or_uri` | `str \| Path \| dict \| None` | Yes | `None` | Usually |
| `save` | `bool` | Yes | `False` | Situational |
| `source_type` | `str` | Yes | `"unknown"` | Usually |
| `description` | `str \| None` | Yes | `None` | Situational |
| `force_save` | `bool` | Yes | `False` | Rarely |
| `max_archive_bytes` | `int` | Yes | `5 * 1024**3` | Usually |
| `max_archive_files` | `int` | Yes | `2_000_000` | Usually |

### Parameter notes

- `name`: Display name for the pretrained reference.
- `path_or_uri`: Local path or logical model identifier such as a Hugging Face model name.
- `save`: Archive the referenced local artifact.
- `source_type`: Source label such as `huggingface`, `torchvision`, or `local`.
- `description`: Optional human-readable note.
- `force_save`: Override archive safety checks.
- `max_archive_bytes` / `max_archive_files`: Safety limits for archive mode.

```python
run.log_pretrained(
    "bert-base",
    path_or_uri="bert-base-uncased",
    source_type="huggingface",
    description="starting checkpoint",
)
```

Like datasets, pretrained references can be:

- metadata only
- archived when `save=True`

Archiving is useful for local checkpoints that you want preserved with the run.

---

## Output scanning { #sdk-output-scanning }

Runicorn can watch generated outputs and archive them into the run.

This is especially useful for:

- checkpoints
- evaluation reports
- generated JSON summaries
- sample outputs written by training scripts

### One-shot scan

<div class="rn-sig" markdown>

**Signature**:
```python
def scan_outputs_once(
    *,
    output_dirs: list[str | Path],
    patterns: list[str] | None = None,
    stable_required: int = 2,
    min_age_sec: float = 1.0,
    mode: str = "rolling",
    log_snapshot_interval_sec: float = 60.0,
    state_gc_after_sec: float = 7 * 24 * 3600,
) -> dict
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `output_dirs` | `list[str \| Path]` | No | none | Yes |
| `patterns` | `list[str] \| None` | Yes | `None` | Usually |
| `stable_required` | `int` | Yes | `2` | Usually |
| `min_age_sec` | `float` | Yes | `1.0` | Usually |
| `mode` | `str` | Yes | `"rolling"` | Usually |
| `log_snapshot_interval_sec` | `float` | Yes | `60.0` | Situational |
| `state_gc_after_sec` | `float` | Yes | `7 * 24 * 3600` | Usually |

### Parameter notes

- `output_dirs`: One or more directories to scan.
- `patterns`: File or directory patterns to track.
- `stable_required`: Number of stable observations required before archiving.
- `min_age_sec`: Minimum age before a candidate output is considered stable enough.
- `mode`: `rolling` updates the logical output entry; advanced workflows may use version-preserving behavior.
- `log_snapshot_interval_sec`: Useful for throttling repeated log-like file snapshots.
- `state_gc_after_sec`: Garbage-collection window for scanner state.

```python
result = run.scan_outputs_once(
    output_dirs=["./outputs"],
    patterns=["*.ckpt", "*.json"],
    stable_required=1,
    min_age_sec=0,
)
```

The returned result dict includes fields such as:

- `scanned`
- `archived`
- `changed`
- `archived_entries`

### Background watcher

<div class="rn-sig" markdown>

**Signature**:
```python
def watch_outputs(
    *,
    output_dirs: list[str | Path],
    interval_sec: float = 10.0,
    patterns: list[str] | None = None,
    stable_required: int = 2,
    min_age_sec: float = 1.0,
    mode: str = "rolling",
    log_snapshot_interval_sec: float = 60.0,
    state_gc_after_sec: float = 7 * 24 * 3600,
) -> None
```
</div>

| Parameter | Type | Optional | Default | Recommended |
|-----------|------|----------|---------|-------------|
| `output_dirs` | `list[str \| Path]` | No | none | Yes |
| `interval_sec` | `float` | Yes | `10.0` | Usually |
| `patterns` | `list[str] \| None` | Yes | `None` | Usually |
| `stable_required` | `int` | Yes | `2` | Usually |
| `min_age_sec` | `float` | Yes | `1.0` | Usually |
| `mode` | `str` | Yes | `"rolling"` | Usually |
| `log_snapshot_interval_sec` | `float` | Yes | `60.0` | Situational |
| `state_gc_after_sec` | `float` | Yes | `7 * 24 * 3600` | Usually |

```python
run.watch_outputs(
    output_dirs=["./outputs"],
    interval_sec=10.0,
    patterns=["*.ckpt", "*.json"],
)
```

Stop it explicitly if you need to:

<div class="rn-sig" markdown>

**Signature**:
```python
def stop_outputs_watch() -> None
```
</div>

```python
run.stop_outputs_watch()
```

### Output modes

The default mode is `rolling`, which updates the asset entry for the same logical output key.

For advanced workflows, Runicorn also supports a version-preserving mode through the underlying output scanner behavior, which is useful if you want to keep multiple output revisions instead of replacing the previous logical slot.

---

## Practical examples

### Training with code snapshot plus output watcher

```python
with rn.init(
    path="cv/resnet50/long-run",
    snapshot_code=True,
) as run:
    run.watch_outputs(
        output_dirs=["./checkpoints", "./reports"],
        patterns=["*.pt", "*.json"],
        interval_sec=15.0,
    )
```

### Dataset plus pretrained reference

```python
with rn.init(path="nlp/bert-finetune/base") as run:
    run.log_dataset("train", "./data/train", context="train")
    run.log_pretrained(
        "bert-base-uncased",
        path_or_uri="bert-base-uncased",
        source_type="huggingface",
    )
```

---

## Best practices

!!! tip "Use metadata-only mode for very large inputs"

    Archive small, important assets. Reference huge datasets by path or logical URI.

!!! tip "Use output scanning for generated artifacts, not for your whole project tree"

    Point `watch_outputs()` at specific directories such as `checkpoints/` or `reports/`.

!!! tip "Snapshot code early, not at the end"

    `snapshot_code=True` captures the workspace as it looked when the run started.

---

## Next steps

- [Run Lifecycle](run-lifecycle.md)
- [Integrations](integrations.md)
- [Logs, Assets & Images](../ui/logs-assets-and-images.md)
