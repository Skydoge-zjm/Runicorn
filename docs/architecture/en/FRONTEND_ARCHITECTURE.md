[English](FRONTEND_ARCHITECTURE.md) | [简体中文](../zh/FRONTEND_ARCHITECTURE.md)

---

# Frontend Architecture

**Document Type**: Architecture  
**Purpose**: React application design and patterns

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
│   └── SettingsDrawer.tsx
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

**Related**: [API_DESIGN.md](API_DESIGN.md) | [COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)

**Back to**: [Architecture Index](README.md)

