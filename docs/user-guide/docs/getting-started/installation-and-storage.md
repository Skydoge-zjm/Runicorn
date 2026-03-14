# Installation & Storage

This page covers how to install Runicorn and how to choose a storage root that works well for daily use.

If you only want the fastest possible first-run path, read [Quick Start](quickstart.md) first and come back here for the fuller setup details.

---

## Installation options

### Latest release

```bash
pip install -U runicorn
```

---

## Recommended storage setup

Set one persistent root and reuse it across projects:

```bash
runicorn config --set-user-root "E:\RunicornData"
runicorn config --show
```

Typical choices:

- Windows: `E:\RunicornData` or `%USERPROFILE%\RunicornData`
- Linux: `/data/runicorn` or `~/runicorn-data`
- macOS: `~/runicorn-data`

---

## Storage resolution order

Runicorn chooses storage in this order:

1. `rn.init(storage=...)`
2. `RUNICORN_DIR`
3. `runicorn config --set-user-root ...`
4. `./.runicorn`

That means you can keep one default root but still override it for specific experiments or scripts.

---

## What the storage root contains

The current layout is path-based:

```text
storage_root/
├─ runs/
│  └─ <path segments>/
│     └─ <run_id>/
├─ archive/
└─ runicorn.db
```

In practice you will mostly care about:

- `runs/`: the actual run folders
- `archive/`: archived assets and deduplicated content
- `runicorn.db`: the local index used by the viewer

---

## Storage from the UI

You can also change the storage root from the settings drawer inside the Web UI. The CLI route is still the easiest way to make the initial setup explicit and reproducible.

---

## Good habits

!!! tip "Use one stable storage root per machine"

    Avoid bouncing between temporary folders unless you are testing.

!!! tip "Use hierarchical paths in code"

    Paths such as `cv/classification/resnet50/baseline` make the tree view and exports much easier to manage.

!!! tip "Keep remote and local roots intentional"

    Remote Viewer does not require the same storage root on the local and remote machine.

---

## Next steps

- [Quick Start](quickstart.md)
- [Python SDK Overview](../sdk/overview.md)
- [CLI Common Workflows](../cli/common-workflows.md)
- [Troubleshooting](../reference/troubleshooting.md)
