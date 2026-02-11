# Quick Start

Get Runicorn up and running in 5 minutes!

---

## Installation

### Step 1: Install Runicorn

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

### Step 2: Verify Installation

```bash
runicorn --version
```

You should see: `runicorn 0.6.0` (or later)

---

## Your First Experiment

### Step 1: Create a Simple Experiment

Create a file `demo.py`:

```python
import runicorn as rn
import random
import time

# Initialize experiment with path-based hierarchy
run = rn.init(path="quickstart/demo_experiment")
print(f"✓ Created experiment: {run.id}")

# Set primary metric (optional)
run.set_primary_metric("accuracy", mode="max")

# Training loop
for step in range(1, 51):
    # Simulate training
    loss = 2.0 * (0.9 ** step) + random.uniform(-0.05, 0.05)
    accuracy = min(0.98, 0.5 + step * 0.01 + random.uniform(-0.02, 0.02))
    
    # Log metrics
    run.log({
        "loss": round(loss, 4),
        "accuracy": round(accuracy, 4),
        "learning_rate": 0.001
    }, step=step)
    
    # Simulate time passing
    time.sleep(0.1)
    
    # Print progress
    if step % 10 == 0:
        print(f"Step {step}/50: loss={loss:.4f}, acc={accuracy:.4f}")

# Save summary
run.summary({
    "final_accuracy": 0.95,
    "total_steps": 50,
    "notes": "Demo experiment from quickstart guide"
})

# Finish experiment
run.finish()
print("✓ Experiment completed!")
```

### Step 2: Run the Experiment

```bash
python demo.py
```

**Expected output**:
```
✓ Created experiment: 20250114_153045_a1b2c3
Step 10/50: loss=0.6974, acc=0.6234
Step 20/50: loss=0.2433, acc=0.7156
Step 30/50: loss=0.0849, acc=0.8089
Step 40/50: loss=0.0296, acc=0.8945
Step 50/50: loss=0.0103, acc=0.9567
✓ Experiment completed!
```

### Step 3: View Results

Start the web viewer:

```bash
runicorn viewer
```

**Open your browser**: [http://127.0.0.1:23300](http://127.0.0.1:23300)

You should see your experiment in the list!

<figure markdown>
  ![Experiments List](../assets/experiment_list.png)
  <figcaption>View all experiments in the Web UI</figcaption>
</figure>

---

## Explore the Web Interface

Click on any experiment to see interactive metric charts, real-time logs, logged images, and workspace assets.

See [Web UI Overview](../ui/overview.md) for a full tour of all pages and features.

---

## Configure Storage

### Set Storage Location

!!! warning "Important First Step"
    The first time you run Runicorn, configure where to store your data.

**Option 1: Web UI**

1. Click the ⚙️ Settings icon (top-right)
2. Go to "Data Directory" tab
3. Enter path: `E:\RunicornData` (or your preferred location)
4. Click "Save Data Directory"

**Option 2: Command Line**

```bash
runicorn config --set-user-root "E:\RunicornData"
```

**Option 3: Code**

```python
import runicorn as rn

run = rn.init(
    path="demo",
    storage="E:\\RunicornData"  # Explicit path
)
```

### Storage Priority

Runicorn determines storage location in this order:

1. `rn.init(storage="...")` - Highest priority
2. Environment variable `RUNICORN_DIR`
3. User config (set via UI/CLI)
4. `./.runicorn/` in current directory - Lowest priority

---

## What's Next?

### Learn More

- [📖 Python SDK Overview](../sdk/overview.md) - Learn all SDK functions
- [💻 CLI Overview](../cli/overview.md) - Command-line tools
- [🖼️ Image Classification Tutorial](../tutorials/image-classification.md) - Complete PyTorch example
- [❓ FAQ](../reference/faq.md) - Frequently asked questions

---

## Getting Help

!!! question "Need help?"

    - 📖 Search this documentation
    - ❓ Check [FAQ](../reference/faq.md)
    - 🐛 [Report issues](https://github.com/Skydoge-zjm/Runicorn/issues)
    - 💬 Ask in [GitHub Discussions](https://github.com/Skydoge-zjm/Runicorn/discussions)


