[English](FRONTEND_ARCHITECTURE.md) | [简体中文](../zh/FRONTEND_ARCHITECTURE.md)

---

# Frontend Architecture

**Document Type**: Architecture  
**Purpose**: React application design and patterns  
**Version**: v0.6.0  
**Last Updated**: 2025-01-XX

---

## Application Structure

```
src/
├── App.tsx                # Root component
├── main.tsx               # Entry point
├── api.ts                 # Centralized API client
├── i18n.ts                # Internationalization
│
├── pages/                 # Page components
│   ├── ExperimentPage.tsx
│   ├── RunDetailPage.tsx
│   ├── ArtifactsPage.tsx
│   └── UnifiedRemotePage.tsx
│
├── components/            # Reusable components
│   ├── MetricChart.tsx
│   ├── LogsViewer.tsx
│   ├── LineageGraph.tsx
│   ├── SettingsDrawer.tsx
│   ├── PathTreePanel.tsx      # v0.6.0 - Path tree navigation
│   ├── CompareChartsView.tsx  # v0.6.0 - Multi-run comparison
│   └── CompareRunsPanel.tsx   # v0.6.0 - Compare mode panel
│
├── contexts/              # React Context
│   └── SettingsContext.tsx
│
├── hooks/                 # Custom hooks
│   └── useColumnWidths.ts
│
├── utils/                 # Utility functions
│   ├── format.ts
│   └── logger.ts
│
└── styles/                # Design system
    ├── designTokens.ts
    └── resizable-table.css
```

---

## State Management

### Context API Pattern

```typescript
// Global settings in Context
const SettingsContext = createContext<{
  settings: UiSettings
  setSettings: (s: UiSettings) => void
}>()

// Provider in App.tsx
<SettingsProvider value={{ settings, setSettings }}>
  <Routes>...</Routes>
</SettingsProvider>

// Consume in components
const { settings } = useSettings()
```

### localStorage Persistence

```typescript
// Save settings
useEffect(() => {
  localStorage.setItem('ui_settings', JSON.stringify(settings))
}, [settings])

// Load settings
const [settings, setSettings] = useState(() => {
  const saved = localStorage.getItem('ui_settings')
  return saved ? JSON.parse(saved) : defaultSettings
})
```

---

## Component Patterns

### Smart vs Dumb Components

**Smart** (Container):
```typescript
// Fetches data, manages state
function RunDetailPage() {
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchRunDetail(id).then(setRun).finally(() => setLoading(false))
  }, [id])
  
  return <RunDetailView run={run} loading={loading} />
}
```

**Dumb** (Presentational):
```typescript
// Only renders, no data fetching
function RunDetailView({ run, loading }) {
  if (loading) return <Skeleton />
  return <div>{run.name}</div>
}
```

---

### React.memo Optimization

```typescript
// Expensive chart component
const MetricChart = memo(({ metrics, title }) => {
  // Complex rendering logic
  return <EChartsReact option={option} />
}, (prevProps, nextProps) => {
  // Custom comparison - only re-render if data changed
  return prevProps.metrics === nextProps.metrics &&
         prevProps.title === nextProps.title
})
```

---

## Performance Optimizations

### Code Splitting

```javascript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'react-vendor': ['react', 'react-dom'],
        'antd-vendor': ['antd', '@ant-design/icons'],
        'echarts-vendor': ['echarts', 'echarts-for-react']
      }
    }
  }
}

// Result: 3 vendor bundles + app code
// Browsers cache vendors separately
```

### Virtual Scrolling

```typescript
// Ant Design Table with virtual scrolling
<Table
  dataSource={10000items}
  virtual                    // Enable virtual scrolling
  scroll={{ y: 600 }}        // Fixed height
/>
// Renders only visible rows + buffer
```

---

## Design System

### Design Tokens

```typescript
export const designTokens = {
  spacing: {
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24
  },
  colors: {
    primary: '#1677ff',
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f'
  },
  typography: {
    fontSize: {
      xs: 12,
      sm: 14,
      md: 16,
      lg: 18
    }
  }
}
```

**Usage**:
```typescript
<Card style={{
  padding: designTokens.spacing.md,
  borderRadius: designTokens.borderRadius.md
}}>
```

---

## API Communication

### Centralized API Client

```typescript
// api.ts
const BASE_URL = import.meta.env.VITE_API_BASE || '/api'

export async function listRuns() {
  const res = await fetch(`${BASE_URL}/runs`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// Usage in components
import { listRuns } from '../api'

const runs = await listRuns()
```

**Benefits**:
- Single source of truth for URLs
- Consistent error handling
- Easy to mock for testing
- Type-safe with TypeScript

---

## Performance Optimizations (v0.5.3) ⚡

### Unified MetricChart Component

**v0.5.3** introduces a unified `MetricChart` component that handles both single-run and multi-run (comparison) scenarios:

```typescript
// Unified interface for single and multi-run charts
interface MetricChartProps {
  runs: RunMetric[]      // Single run: [{ id, metrics }], Multi-run: multiple entries
  xKey: string           // X-axis key (global_step, time, etc.)
  yKey: string           // Y-axis metric key
  title: string
  height?: number | string
  persistKey?: string    // localStorage key for control persistence
  group?: string         // ECharts group for synchronized zoom
}

// Usage - Single run
<MetricChart 
  runs={[{ id: runId, metrics: stepMetrics }]} 
  xKey="global_step" 
  yKey="loss" 
  title="Training Loss" 
/>

// Usage - Multi-run comparison
<MetricChart 
  runs={selectedRuns.map(r => ({ id: r.id, label: r.name, metrics: r.metrics }))}
  xKey="global_step" 
  yKey="loss" 
  title="Loss Comparison" 
/>
```

**Benefits**:
- Single codebase for all metric visualizations
- Consistent behavior across single and comparison views
- Reduced bundle size (removed `MultiRunMetricChart.tsx`)
- Easier maintenance and feature additions

### Lazy Chart Loading

Charts are lazily loaded using `IntersectionObserver`:

```typescript
function LazyChartWrapper({ children, height = 320, threshold = 0.1 }) {
  const ref = useRef<HTMLDivElement>(null)
  const [hasLoaded, setHasLoaded] = useState(false)

  useEffect(() => {
    if (hasLoaded) return
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasLoaded(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px', threshold }  // Pre-load 200px before viewport
    )

    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [hasLoaded, threshold])

  return (
    <div ref={ref} style={{ minHeight: height }}>
      {hasLoaded ? children : <Skeleton />}
    </div>
  )
}
```

**Benefits**:
- Faster initial page load (charts outside viewport are not rendered)
- Reduced memory usage for pages with many charts
- Pre-loading (200px) ensures smooth scrolling experience

### Advanced Memo Optimization

Custom memo comparison using data fingerprints:

```typescript
const MetricChart = memo(function MetricChart({ runs, xKey, yKey, ... }) {
  // Component implementation
}, (prevProps, nextProps) => {
  // Compare runs array by fingerprint, not reference
  if (prevProps.runs.length !== nextProps.runs.length) return false
  
  for (let i = 0; i < prevProps.runs.length; i++) {
    const prevRun = prevProps.runs[i]
    const nextRun = nextProps.runs[i]
    
    if (prevRun.id !== nextRun.id) return false
    if (prevRun.label !== nextRun.label) return false
    
    // Compare by row count and last step (fingerprint)
    const prevRowCount = prevRun.metrics?.rows?.length ?? 0
    const nextRowCount = nextRun.metrics?.rows?.length ?? 0
    if (prevRowCount !== nextRowCount) return false
    
    if (prevRowCount > 0) {
      const prevLastStep = prevRun.metrics.rows[prevRowCount - 1]?.global_step
      const nextLastStep = nextRun.metrics.rows[nextRowCount - 1]?.global_step
      if (prevLastStep !== nextLastStep) return false
    }
  }
  
  return prevProps.xKey === nextProps.xKey && prevProps.yKey === nextProps.yKey
})
```

**Benefits**:
- Prevents unnecessary re-renders when data reference changes but content is same
- O(1) comparison instead of deep equality check
- Significant performance improvement for real-time updates

### Backend Integration: LTTB Downsampling

Frontend integrates with backend LTTB (Largest-Triangle-Three-Buckets) downsampling:

```typescript
// api.ts - Pass maxDataPoints from settings
export async function getStepMetrics(runId: string, downsample?: number) {
  const params = downsample ? `?downsample=${downsample}` : ''
  const res = await fetch(`${BASE_URL}/runs/${runId}/metrics_step${params}`)
  return res.json()
}

// RunDetailPage.tsx - Use settings.maxDataPoints
const { settings } = useSettings()
const metrics = await getStepMetrics(runId, settings.maxDataPoints)

// Response includes total before downsampling
// { columns: [...], rows: [...], total: 100000, sampled: 2000 }
```

**Benefits**:
- Reduces data transfer for large experiments (100k+ points → 2k points)
- LTTB preserves visual characteristics of the data
- Configurable via UI settings

---

## New Frontend Features (v0.6.0) 🆕

### Path Tree Navigation

**Component**: `PathTreePanel.tsx`

The ExperimentPage now includes a VSCode-style path tree panel for hierarchical navigation:

```typescript
// ExperimentPage layout with PathTreePanel
<Layout>
  <Sider width={240}>
    <PathTreePanel
      selectedPath={selectedPath}
      onSelectPath={setSelectedPath}
      onBatchDelete={handleBatchDelete}
      onBatchExport={handleBatchExport}
    />
  </Sider>
  <Content>
    <ExperimentTable pathFilter={selectedPath} />
  </Content>
</Layout>
```

**Features**:
- Hierarchical folder structure with expand/collapse
- Run count badges with running indicator animation
- Search/filter paths
- Right-click context menu for batch operations
- Persistent expanded state in localStorage

### Inline Compare View

**Components**: `CompareRunsPanel.tsx`, `CompareChartsView.tsx`

Multi-run comparison directly in the experiment list page:

```typescript
// Compare mode layout
{compareMode ? (
  <Layout>
    <Sider width={280}>
      <CompareRunsPanel
        runs={selectedRuns}
        colors={chartColors}
        visibleRunIds={visibleRunIds}
        onToggleRunVisibility={toggleRunVisibility}
        onBack={() => setCompareMode(false)}
      />
    </Sider>
    <Content>
      <CompareChartsView
        runIds={selectedRunIds}
        visibleRunIds={visibleRunIds}
        metricsMap={metricsMap}
        runLabels={runLabels}
        colors={chartColors}
        loading={loading}
      />
    </Content>
  </Layout>
) : (
  <ExperimentTable onCompare={enterCompareMode} />
)}
```

**Key Features**:
- Auto-detect common metrics across selected runs
- Toggle individual run/metric visibility
- ECharts group synchronization for linked zoom
- Color-coded run identification

### Enhanced LogsViewer

**Component**: `LogsViewer.tsx`

Terminal-style log viewer with full ANSI color support:

```typescript
// ANSI color rendering
const ansiConverter = new AnsiToHtml({
  fg: '#e6e9ef',
  bg: '#0b1020',
  colors: { /* terminal color palette */ }
})

// Render with line numbers and search highlighting
{displayLines.map((line, index) => (
  <div className="log-line">
    <span className="line-number">{index + 1}</span>
    <span dangerouslySetInnerHTML={{ __html: ansiConverter.toHtml(line) }} />
  </div>
))}
```

**Features**:
- Full ANSI escape code support (colors, bold, etc.)
- Line numbers for easy reference
- Keyword search with highlighting
- Smart tqdm progress bar filtering
- Auto-scroll toggle
- Copy all / Clear buttons

---

## Remote Viewer Frontend (v0.5.0)

### New Pages and Components

```
src/pages/
├── RemoteConnectionPage.tsx   # Remote connection management
└── RemoteViewerPage.tsx       # Remote Viewer control page

src/components/remote/
├── ConnectionForm.tsx          # SSH connection form
├── EnvironmentSelector.tsx    # Environment selector
├── ViewerStatusIndicator.tsx  # Viewer status indicator
└── ConnectionList.tsx          # Connection list
```

### State Management (Remote)

**Connection state**:
```typescript
interface RemoteConnection {
  connection_id: string
  host: string
  username: string
  status: 'connected' | 'disconnected' | 'connecting'
  has_viewer: boolean
  viewer_url?: string
  health?: HealthStatus
}

// Periodic health polling
useEffect(() => {
  const interval = setInterval(async () => {
    for (const conn of connections) {
      const health = await checkConnectionHealth(conn.connection_id)
      updateConnectionHealth(conn.connection_id, health)
    }
  }, 30000)  // Every 30 seconds
  
  return () => clearInterval(interval)
}, [connections])
```

### Remote Connection Flow (UI)

**Step 1: Connection form**, **Step 2: Environment selection**, **Step 3: Start Viewer** - Complete UI flow with loading states, error handling, and success feedback.

### Real-time Health Monitoring

```typescript
function useConnectionHealth(connectionId: string, interval = 30000) {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  
  useEffect(() => {
    if (!connectionId) return
    checkHealth(connectionId).then(setHealth)
    
    const timer = setInterval(() => {
      checkHealth(connectionId).then(setHealth)
    }, interval)
    
    return () => clearInterval(timer)
  }, [connectionId, interval])
  
  return health
}
```

### Error Handling (Frontend)

Remote-specific error handlers with contextual messages, suggestions, and recovery actions for SSH auth failures, environment detection issues, and Viewer startup problems.

---

**Related**: [API_DESIGN.md](API_DESIGN.md) | [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md) | [REMOTE_VIEWER_ARCHITECTURE.md](REMOTE_VIEWER_ARCHITECTURE.md)

**Back to**: [Architecture Index](README.md)

