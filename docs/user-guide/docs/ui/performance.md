# Performance Tips

Optimize Runicorn for large experiments and smooth performance.

---

## Overview

Runicorn v0.5.x introduces significant performance improvements:

| Version | Feature | Benefit |
|---------|---------|---------|
| **v0.5.2** | LTTB Downsampling | Handle 100k+ data points |
| **v0.5.2** | Incremental Cache | Faster file parsing |
| **v0.5.3** | Lazy Chart Loading | Faster page load |
| **v0.5.3** | Memo Optimization | Fewer re-renders |

---

## LTTB Downsampling

**Problem**: Charts become slow with 100,000+ data points.

**Solution**: LTTB (Largest-Triangle-Three-Buckets) algorithm reduces data while preserving visual characteristics.

### How It Works

```
Original: 100,000 points → LTTB → 2,000 points
```

LTTB intelligently selects representative points that maintain the shape of your curves.

### Configuration

In **Settings** (⚙️) → **Charts**:

| Setting | Default | Description |
|---------|---------|-------------|
| **Max Data Points** | 2000 | Target number of points after downsampling |

!!! tip "Recommended Values"
    - **2000** (default) — Good balance for most displays
    - **5000** — Higher fidelity, slightly slower
    - **1000** — Faster rendering, less detail

### API Parameter

The backend supports explicit downsampling:

```bash
# API request with downsampling
GET /api/runs/{run_id}/metrics_step?downsample=2000
```

Response includes original count:
```json
{
  "columns": ["global_step", "loss"],
  "rows": [...],
  "total": 100000,
  "sampled": 2000
}
```

---

## Incremental Caching

**Problem**: Re-parsing large metrics files is slow.

**Solution**: Incremental cache reads only new data since last access.

### How It Works

```
First request:  Parse entire file (1.5s)
Second request: Read from cache (5ms) ← 300x faster!
New data:       Parse only new lines (50ms)
```

### Cache Statistics

Check cache performance:

```bash
GET /api/metrics/cache/stats
```

Response:
```json
{
  "entries": 42,
  "hits": 1250,
  "misses": 42,
  "incremental_updates": 380,
  "hit_rate": 0.97
}
```

!!! info "Automatic Management"
    The cache is fully automatic with LRU eviction. No configuration needed.

---

## Lazy Chart Loading

**Problem**: Pages with many charts load slowly.

**Solution**: Charts are lazily loaded as they enter the viewport.

### How It Works

```
Page Load → Only visible charts render
Scroll Down → Charts load 200px before entering viewport
```

### Benefits

- ⚡ **Faster initial load** — Only 2-3 visible charts render immediately
- 💾 **Lower memory usage** — Unused charts don't consume resources
- 🔄 **Smooth scrolling** — Pre-loading prevents jank

!!! tip "Skeleton Placeholders"
    You'll see skeleton placeholders for unloaded charts. They automatically load as you scroll.

---

## Memo Optimization

**Problem**: Charts re-render unnecessarily during real-time updates.

**Solution**: Smart comparison using data fingerprints.

### How It Works

Instead of deep equality checks, Runicorn compares:

```typescript
// Fingerprint comparison (O(1))
if (prevRowCount !== nextRowCount) return false
if (prevLastStep !== nextLastStep) return false
return true  // No re-render needed
```

### Benefits

- ⚡ **Fewer re-renders** — Only update when data actually changes
- 🔋 **Lower CPU usage** — Especially important for real-time monitoring
- 📊 **Smoother animations** — No unnecessary chart redraws

---

## Best Practices

### For Large Experiments (100k+ steps)

1. **Enable downsampling** — Set Max Data Points to 2000-5000
2. **Use step-based metrics** — More efficient than time-based
3. **Limit logged metrics** — Only log essential metrics frequently

```python
# Good: Log sparingly
if step % 100 == 0:
    run.log({"loss": loss}, step=step)

# Avoid: Logging every step
run.log({"loss": loss}, step=step)  # 100x more data
```

### For Many Experiments (1000+)

1. **Use path hierarchy** — Organize experiments with descriptive paths for filtering
2. **Archive old experiments** — Export and remove completed experiments
3. **Use V2 API** — Frontend automatically uses faster queries

### For Real-time Monitoring

1. **Reasonable refresh rate** — Default 5s is usually sufficient
2. **Limit chart count** — Collapse unused metric groups
3. **Use log smoothing** — EMA reduces visual noise

---

## Monitoring Performance

### Browser DevTools

1. Open DevTools (F12)
2. Go to **Network** tab
3. Filter by "api"
4. Check response times

**Healthy metrics**:

| Endpoint | Expected Time |
|----------|---------------|
| `/api/runs` | < 500ms |
| `/api/runs/{id}/metrics_step` | < 200ms |
| Cache hit | < 50ms |

### Response Headers

API responses include timing info:

| Header | Description |
|--------|-------------|
| `X-Row-Count` | Rows in response |
| `X-Total-Count` | Total rows before downsampling |
| `X-Last-Step` | Last step number |

---

## Troubleshooting

### Charts Loading Slowly

1. ✅ Check Max Data Points setting (reduce if > 5000)
2. ✅ Verify cache is working (check `/api/metrics/cache/stats`)
3. ✅ Reduce number of visible charts

### High Memory Usage

1. ✅ Close unused browser tabs
2. ✅ Reduce chart refresh rate
3. ✅ Enable lazy loading (default in v0.5.3+)

### UI Feels Sluggish

1. ✅ Check network latency (should be < 100ms)
2. ✅ Disable chart animations in settings
3. ✅ Use Chrome/Edge for best performance

---

## Technical Details

### Cache Architecture

```
IncrementalMetricsCache
├── File size-based invalidation
├── LRU eviction (max 1000 entries)
├── Thread-safe operations
└── Automatic stale entry cleanup
```

### Frontend Optimizations

```
MetricChart Component
├── React.memo with fingerprint comparison
├── useMemo for expensive computations
├── IntersectionObserver for lazy loading
└── ECharts instance recycling
```

---

<div align="center">
  <p><strong>Need more speed?</strong></p>
  <p>Check the <a href="../reference/faq.md">FAQ</a> or <a href="https://github.com/Skydoge-zjm/Runicorn/issues">report an issue</a>.</p>
</div>
