# Path-based Hierarchy

Runicorn uses a single `path` field to organize experiments. This page focuses on how to design that hierarchy so the UI and storage layout stay useful over time.

You do not need to master this page before your very first run. It becomes most useful once you have a few experiments and want a naming scheme that will scale cleanly.

---

## Why `path` matters

`path` affects more than naming. It directly shapes:

- the tree view in the experiments page
- how runs are grouped and filtered
- which runs naturally belong together for comparison
- subtree export and delete operations
- how understandable your storage layout stays as runs accumulate

If paths are consistent, the UI gets better as the project grows. If paths are chaotic, the tree becomes noise.

---

## Designing your hierarchy

Instead of separate `project` and `name` fields, Runicorn expects one hierarchical string:

```python
import runicorn as rn

run = rn.init(path="cv/classification/resnet50/baseline")
```

The important rule is not a specific template. The important rule is that the hierarchy should match **your own workflow**.

### Engineering-style examples

```text
cv/classification/resnet50/baseline
cv/detection/yolov8/augmented
nlp/text-classification/bert-base/lr-1e5
```

### Research-style examples

```text
sr_project/swinir/reproduction/table_1_acc
sr_project/my_new_method/ablation/loss_term_b
project/paper_x/reproduction/main_result
```

Runicorn requires hierarchy, not a specific taxonomy.

### What belongs in `path`

Use `path` for the long-lived bucket a run belongs to:

- domain or project
- task
- model family or method family
- major variant, regime, or target result

### What usually does *not* belong in `path`

Run-specific detail is often better stored elsewhere:

- `alias` for a short human label
- tags for lightweight grouping
- `summary()` for final notes or outcomes

Good pattern:

```python
run = rn.init(
    path="sr_project/swinir/reproduction/table_1_acc",
    alias="seed-42",
)
```

Less helpful pattern:

```python
run = rn.init(
    path="sr_project/swinir/reproduction/table_1_acc/seed-42/lr-1e4/bs-16"
)
```

unless those extra dimensions are truly part of the permanent hierarchy you want to browse every day.

---

## Quick examples

```python
# Small personal experiment
rn.init(path="demo")

# Former project/name-style structure
rn.init(path="cv/resnet50")

# Engineering-style deeper hierarchy
rn.init(path="cv/detection/yolov8/augmented")

# Research-style hierarchy
rn.init(path="sr_project/swinir/reproduction/table_1_acc")

# Root-level runs
rn.init(path="/")

# Default path
rn.init()  # becomes "default"
```

---

## Team conventions

If multiple people write into the same storage root, agree on one shared scheme early.

Common patterns include:

```text
domain/task/model/variant
```

```text
team-or-domain/task/model/dataset-or-regime
```

```text
project/paper_or_method/reproduction_or_ablation/target
```

The exact pattern matters less than consistency. A simple convention is much better than every person inventing a new path style.

---

## Validation rules

Runicorn validates and normalizes paths.

### Allowed characters

- letters
- numbers
- underscores `_`
- hyphens `-`
- forward slashes `/`

### Invalid examples

```python
rn.init(path="my experiment")   # spaces not allowed
rn.init(path="path/../escape")  # traversal-like input rejected
rn.init(path="special@chars!")  # special characters not allowed
```

### Normalization rules

- backslashes are converted to `/`
- leading and trailing slashes are stripped
- `"/"` or `""` maps to the root path
- `None` becomes `"default"`
- maximum length is 200 characters

---

## Filesystem layout

Paths map directly under the storage root:

```text
storage_root/
├─ runs/
│  ├─ cv/
│  │  └─ classification/
│  │     └─ resnet50/
│  │        └─ baseline/
│  │           └─ 20260115_120000_789abc/
│  └─ sr_project/
│     └─ swinir/
│        └─ reproduction/
│           └─ table_1_acc/
│              └─ 20260115_130000_xyz789/
└─ archive/
```

This is one reason consistent paths pay off: your storage layout remains understandable outside the UI too.

---

## How the UI uses it

The experiments page tree uses the path hierarchy directly. That enables:

- collapsible navigation
- subtree filtering
- folder creation and delete flows
- subtree export
- path-based batch actions

This is why stable, predictable paths are worth the effort.

---

## Migration from old `project/name`

If you still think in the old `project` + `name` style, the simplest migration is:

### Before

```python
run = rn.init(project="image_classification", name="resnet50_v1")
```

### After

```python
run = rn.init(path="image_classification/resnet50_v1")
```

You can also take the chance to add more structure:

```python
run = rn.init(path="cv/classification/resnet50/v1")
```

---

## Best practices

!!! tip "Keep reruns in the same path"

    That is what makes the path tree and compare flows useful.

!!! tip "Use alias for run-specific labels"

    Keep `path` stable and let `alias` carry the one-off human name.

!!! tip "Choose a taxonomy that matches your work"

    Engineering teams and research teams often want very different hierarchies. Both are fine.

!!! warning "Do not overfit the hierarchy"

    If your path becomes too deep or too specific, browsing gets worse instead of better.

---

## Next steps

- [Python SDK Overview](../sdk/overview.md)
- [Experiments & Paths](../ui/experiments-and-paths.md)
- [Quick Start](../getting-started/quickstart.md)
