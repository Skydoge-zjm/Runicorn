# Web UI Overview

Runicorn's web interface provides a powerful, modern dashboard for exploring your ML experiments.

---

## Starting the Viewer

```bash
runicorn viewer
```

Open [http://127.0.0.1:23300](http://127.0.0.1:23300) in your browser.

??? tip "Custom Host and Port"
    ```bash
    # Allow access from other machines
    runicorn viewer --host 0.0.0.0 --port 8000
    ```

---

## Main Pages

### 📋 Experiments Page

The home page displays all your experiments in a sortable, filterable table.

**Features**:

- 🔍 **Search** — Filter by path, status, alias
- 📊 **Best Metrics** — See primary metric at a glance
- 🏷️ **Status Badges** — Running, Finished, Failed, Interrupted
- 🗑️ **Soft Delete** — Move to recycle bin (recoverable)
- ✅ **Multi-select** — Batch operations on experiments
- 📥 **Export** — Download experiments as archive

**Column Options**:

| Column | Description |
|--------|-------------|
| ID | Unique experiment identifier |
| Path | Experiment path (hierarchical) |
| Status | Current status with animated badge |
| Created | Creation timestamp |
| Duration | Total runtime |
| Best Metric | Primary metric value and step |

---

### 📈 Experiment Detail Page

Click on any experiment to see detailed information.

#### Metrics Charts

- **Interactive Charts** — Zoom, pan, hover for values
- **EMA Smoothing** — Adjustable smoothing factor (0-1)
- **Log Scale** — Toggle logarithmic Y-axis
- **Dynamic Scale** — Auto-adjust Y-axis range
- **X-Axis Selection** — Switch between step/time/epoch
- **Export CSV** — Download chart data

#### Experiment Comparison (v0.5.3+)

Compare multiple experiments on the same chart:

1. Click **"Compare"** button on detail page
2. Select experiments to overlay
3. View all runs on unified charts

!!! tip "Unified MetricChart"
    v0.5.3 introduces a unified chart component that handles both single-run and comparison views with consistent behavior.

#### Other Tabs

- **Logs** — Real-time log streaming
- **Images** — Logged images and visualizations
- **Assets** — Workspace snapshots and stored files
- **Config** — Environment and configuration info

---

### 🌳 Path Tree Panel (v0.6.0)

VSCode-style hierarchical navigation for experiments organized by path.

**Features**:

- 🗂️ **Tree Navigation** — Browse experiments by path hierarchy
- 📊 **Path Statistics** — Run counts per path node
- 🔍 **Quick Filter** — Filter runs by clicking any path node
- 📥 **Batch Export** — Export all runs under a path
- 🗑️ **Batch Delete** — Soft-delete all runs under a path

---

### 📊 Inline Compare View (v0.6.0)

Compare metrics across multiple runs side-by-side.

<figure markdown>
  ![Inline Compare View](../assets/comparison.png)
  <figcaption>Compare multiple runs with synchronized charts</figcaption>
</figure>

**Features**:

- 📈 **Multi-Run Charts** — Overlay metrics from different runs
- 🔗 **Linked Axes** — Synchronized zooming with ECharts
- 🎯 **Common Metrics** — Auto-detect shared metric keys
- 🎨 **Color Coding** — Distinct colors for each run

---

### 💻 Performance Monitor

Real-time system performance monitoring — CPU, memory, disk, and GPU.

<figure markdown>
  ![Performance Monitor](../assets/hardware_monitor.png)
  <figcaption>Real-time GPU metrics monitoring</figcaption>
</figure>

**Tabs**:

- **CPU** — Usage, frequency, per-core stats
- **Memory & Disk** — RAM usage, disk I/O
- **GPU Metrics** — Utilization, VRAM, power, temperature
- **GPU Telemetry** — Historical GPU usage charts

---

### 🌐 Remote Page (v0.5.0+)

Connect to remote training servers via SSH.

**Features**:

- 🔗 **Connection Manager** — Add/remove SSH connections
- 🐍 **Environment Detection** — Auto-detect Python environments
- 🚀 **Viewer Control** — Start/stop remote Viewer
- ❤️ **Health Monitor** — Connection status and latency

See [Remote Viewer Guide](../getting-started/remote-viewer.md) for details.

---

## Settings

Click the ⚙️ icon (top-right) to access settings.

### Appearance

| Setting | Options | Description |
|---------|---------|-------------|
| **Theme** | Light / Dark / Auto | Color scheme |
| **Accent Color** | Blue, Purple, Green... | Primary accent color |
| **Background** | Gradient / Solid / Image | Page background style |

### Charts

| Setting | Default | Description |
|---------|---------|-------------|
| **Chart Height** | 320px | Default chart height |
| **Max Data Points** | 2000 | LTTB downsampling target |
| **Animations** | On | Enable chart animations |
| **Auto Refresh** | 5s | Real-time update interval |

### Data

| Setting | Description |
|---------|-------------|
| **Data Directory** | Storage root path |
| **Language** | UI language (English/中文) |

!!! info "Settings Persistence"
    All settings are saved in browser localStorage and persist across sessions.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Focus search |
| `Esc` | Close modal/drawer |
| `R` | Refresh data |

---

## Mobile Support

The UI is responsive and works on tablets, though desktop is recommended for the best experience.

---

## Next Steps

- [Remote Viewer Guide](../getting-started/remote-viewer.md) — Access remote experiments
- [FAQ](../reference/faq.md) — Common questions
- [Python SDK](../sdk/overview.md) — Track experiments programmatically

---

<div class="rn-page-nav">
  <a href="../getting-started/remote-viewer.md">Remote Viewer →</a> &middot;
  <a href="../sdk/overview.md">Python SDK →</a>
</div>
