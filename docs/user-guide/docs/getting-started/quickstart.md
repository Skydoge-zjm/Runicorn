# Quick Start

Get Runicorn running quickly with the current 0.7.1 workflow.

This page intentionally focuses on the shortest path from installation to your first visible run.

---

## Step 1: Install Runicorn

```bash
pip install -U runicorn
```

**Requirements**: Python 3.10 or higher

??? tip "Using conda?"
    ```bash
    conda create -n runicorn python=3.10
    conda activate runicorn
    pip install runicorn
    ```

Verify installation:

```bash
runicorn --version
```

---

## Step 2: Choose a storage root

Set a persistent storage location before you start collecting runs:

```bash
runicorn config --set-user-root "E:\RunicornData"
runicorn config --show
```

Runicorn resolves storage in this order:

1. `rn.init(storage=...)`
2. `RUNICORN_DIR`
3. `runicorn config --set-user-root ...`
4. `./.runicorn`

See [Installation & Storage](installation-and-storage.md) for the full layout and platform-specific examples.

---

## Step 3: Run your first experiment

Create `demo.py`:

```python
import random
import time

import runicorn as rn

run = rn.init(
    path="quickstart/demo-experiment",
    alias="baseline",
    capture_console=True,
)
run.set_primary_metric("accuracy", mode="max")

for step in range(1, 51):
    loss = 2.0 * (0.9 ** step) + random.uniform(-0.05, 0.05)
    accuracy = min(0.98, 0.5 + step * 0.01 + random.uniform(-0.02, 0.02))

    run.log({
        "loss": round(loss, 4),
        "accuracy": round(accuracy, 4),
        "learning_rate": 0.001,
    }, step=step)

    time.sleep(0.1)
    if step % 10 == 0:
        print(f"Step {step}/50: loss={loss:.4f}, acc={accuracy:.4f}")

run.summary({
    "final_accuracy": 0.95,
    "total_steps": 50,
    "notes": "Demo experiment from quickstart guide",
})

run.finish()
print("Completed:", run.id)
```

Run it:

```bash
python demo.py
```

---

## Step 4: Open the viewer

Start the local web viewer:

```bash
runicorn viewer
```

Open [http://127.0.0.1:23300](http://127.0.0.1:23300).

You should now see the run in the experiments table.

<figure markdown>
  ![Experiments List](../assets/main_page/experiment_list.png)
  <figcaption>The experiments page is the main entry point for local runs.</figcaption>
</figure>

---

## Step 5: Explore the run

Open the run to inspect:

- charts and best-metric tracking
- live and captured logs
- summary fields
- assets, images, and config metadata

See [Web UI Overview](../ui/overview.md) for the page-by-page tour.

---

## What next?

- [Installation & Storage](installation-and-storage.md)
- [Remote Viewer](remote-viewer.md)
- [Python SDK Overview](../sdk/overview.md)
- [CLI Overview](../cli/overview.md)
- [Image Classification Tutorial](../tutorials/image-classification.md)

---

## Getting help

!!! question "Need help?"

    - Search this documentation
    - Check [FAQ](../reference/faq.md)
    - Read [Troubleshooting](../reference/troubleshooting.md)
    - Report issues on GitHub
