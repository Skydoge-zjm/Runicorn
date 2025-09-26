# Runicorn Migration Guide

This guide helps you migrate to the latest version of Runicorn.

## 🚀 v0.3.1 Improvements (Latest)

### Architecture Modernization
- **Automatic**: No action required - existing code works unchanged
- **Performance**: 10x+ faster experiment queries through SQLite storage
- **Storage**: Automatic creation of `runicorn.db` for enhanced performance
- **Compatibility**: All existing files and workflows continue to work

## 🔄 v0.3.0 Breaking Changes

This section covers migration from v0.2.x to v0.3.0.

## 🔄 Breaking Changes

### 1. Best Metric System Changes

#### What Changed
The hardcoded `best_val_acc_top1` field has been replaced with a universal best metric system.

#### Before (v0.2.x)
```python
import runicorn as rn

run = rn.init(project="demo", name="exp1")
# ... training code ...
rn.summary({"best_val_acc_top1": 95.2})  # Hardcoded field
rn.finish()
```

#### After (v0.3.0)
```python
import runicorn as rn

run = rn.init(project="demo", name="exp1")

# Set your primary metric - can be ANY metric name
rn.set_primary_metric("accuracy", mode="max")  # or "loss", mode="min"

# ... training code ...
rn.log({"accuracy": 95.2, "loss": 0.05})  # Best value auto-tracked

# No need to manually track best value in summary
rn.summary({"final_epoch": 100})  # Other summary data
rn.finish()  # Best metric automatically saved
```

#### Migration Steps
1. Remove any `best_val_acc_top1` references from your code
2. Add `rn.set_primary_metric("your_metric", mode="max|min")` after initialization
3. Continue logging metrics normally - best values are tracked automatically

### 2. Removed Components

#### What Was Removed
- `RunsPage.tsx` - Functionality merged into `ExperimentPage`
- `ComparisonPage.tsx` - Comparison integrated into `RunDetailPage`

#### Impact
- No user-visible changes - all functionality preserved
- Cleaner codebase with reduced duplication

## ✨ New Features to Explore

### 1. Universal Best Metric System

Track any metric as your primary indicator:

```python
# For accuracy-based models
rn.set_primary_metric("val_accuracy", mode="max")

# For loss-based optimization  
rn.set_primary_metric("train_loss", mode="min")

# For custom metrics
rn.set_primary_metric("f1_score", mode="max")
rn.set_primary_metric("error_rate", mode="min")
```

**Result**: Web interface shows `val_accuracy: 94.23` in Best Metric column

### 2. Soft Delete & Recycle Bin

Safe experiment management:

- **Delete**: Click delete → experiments moved to recycle bin (files preserved)
- **Restore**: Open recycle bin → select experiments → restore
- **Permanent Delete**: Empty recycle bin when ready

**Benefits**: No more accidental data loss!

### 3. Smart Status Detection

Automatic handling of experiment crashes:

```python
# Your training code - no changes needed
for epoch in range(100):
    rn.log({"accuracy": train_epoch()})
    # If process crashes here, status automatically becomes "failed"

rn.finish()  # Only called if training completes successfully
```

**Status Types**:
- `running` - Active with PID display
- `finished` - Completed successfully  
- `failed` - Crashed or error
- `interrupted` - User stopped (Ctrl+C)

### 4. Enhanced Settings Interface

Access via gear icon → comprehensive customization:

- **Appearance**: Themes, colors, density
- **Layout**: Backgrounds, glass effects, animations
- **Data**: Storage configuration, import/export
- **Performance**: Refresh intervals, chart settings

### 5. Environment Tracking

Automatic reproducibility:

```python
# Enable environment capture
run = rn.init(project="research", name="exp1", capture_env=True)

# Automatically captures:
# - Git commit, branch, changes
# - Python packages (pip/conda)
# - System specifications
# - Environment variables
```

**Result**: `environment.json` created with complete environment snapshot

### 6. Advanced Export Features

Multiple export formats (optional modules):

```python
# Excel export with charts
if hasattr(rn, 'MetricsExporter'):
    exporter = rn.MetricsExporter(run.run_dir)
    exporter.to_excel("results.xlsx", include_charts=True)
    exporter.to_tensorboard("./tensorboard_logs")
    exporter.generate_report("report.md", format="markdown")
```

### 7. Monitoring & Alerts

Automatic anomaly detection (optional):

```python
# Enable monitoring
if hasattr(rn, 'MetricMonitor'):
    monitor = rn.MetricMonitor()
    # Automatically detects:
    # - NaN/Inf values
    # - Loss explosions
    # - Training instabilities
```

## 🔧 Technical Migration

### Dependencies

Add to your requirements.txt:
```txt
runicorn>=0.3.0
psutil>=5.8.0  # For status detection
```

### Optional Dependencies

For enhanced features:
```bash
# Excel export, charts
pip install pandas openpyxl

# TensorBoard export  
pip install torch tensorboard

# PDF reports
pip install reportlab

# Advanced monitoring
pip install numpy matplotlib
```

## 🚀 Recommended Upgrade Path

1. **Update Package**
   ```bash
   pip install -U runicorn
   ```

2. **Update Your Code**
   ```python
   # Add this line after rn.init()
   rn.set_primary_metric("your_main_metric", mode="max")
   
   # Remove any best_val_acc_top1 references
   # rn.summary({"best_val_acc_top1": value})  # Remove this
   ```

3. **Test New Features**
   ```bash
   python examples/create_test_run.py
   runicorn viewer
   ```

4. **Explore New UI**
   - Try the new settings interface
   - Test soft delete and recycle bin
   - Check responsive design on different window sizes

## 💡 Tips for v0.3.0

### Best Practices

1. **Always set a primary metric** early in your training:
   ```python
   rn.set_primary_metric("val_f1", mode="max")
   ```

2. **Enable environment capture** for reproducibility:
   ```python
   run = rn.init(project="proj", name="exp", capture_env=True)
   ```

3. **Use the new settings** to customize your experience:
   - Adjust chart heights for your screen
   - Configure auto-refresh intervals
   - Customize themes and backgrounds

### Troubleshooting

- **Missing best metric**: Ensure you call `rn.set_primary_metric()` after `rn.init()`
- **Status stuck on running**: Click "Check Status" button or wait for background sync
- **Charts too small**: Adjust "Default Chart Height" in Performance settings

## 🎉 Welcome to v0.3.0!

This release transforms Runicorn from a simple tracking tool into a comprehensive ML experiment management platform. Enjoy the enhanced features!
