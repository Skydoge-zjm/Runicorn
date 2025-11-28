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

- 🔍 **Search** — Filter by project, name, status
- 📊 **Best Metrics** — See primary metric at a glance
- 🏷️ **Status Badges** — Running, Finished, Failed, Interrupted
- 🗑️ **Soft Delete** — Move to recycle bin (recoverable)
- ✅ **Multi-select** — Batch operations on experiments
- 📥 **Export** — Download experiments as archive

**Column Options**:

| Column | Description |
|--------|-------------|
| ID | Unique experiment identifier |
| Project | Project name |
| Name | Experiment name |
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
- **Artifacts** — Associated models and datasets
- **Config** — Environment and configuration info

---

### 📦 Artifacts Page

Git-like version control for ML models and datasets.

**Features**:

- 📦 **List Artifacts** — All versioned assets
- 🔢 **Version History** — v1, v2, v3... with metadata
- 🌳 **Lineage Graph** — Interactive dependency visualization
- 📊 **Storage Stats** — Deduplication savings

**Actions**:

| Action | Description |
|--------|-------------|
| View | See artifact details and metadata |
| Download | Get artifact files |
| Delete | Remove artifact version |
| Compare | Compare versions |

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

- [Performance Tips](performance.md) — Optimize for large experiments
- [FAQ](../reference/faq.md) — Common questions
- [Python SDK](../sdk/overview.md) — Track experiments programmatically

---

<div align="center">
  <p><strong>Explore your experiments with the modern UI!</strong></p>
  <p><code>runicorn viewer</code> → <a href="http://127.0.0.1:23300">http://127.0.0.1:23300</a></p>
</div>
